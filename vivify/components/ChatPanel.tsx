import React, { useState, useRef, useEffect, useCallback, useMemo, memo } from 'react';
import { chatApi } from '../services/chatApi';
import { PaperAirplaneIcon } from './icons/PaperAirplaneIcon';
import { ChatMessage, ModelStep } from '../types';
import { CogIcon } from './icons/CogIcon';
import { TerminalIcon } from './icons/TerminalIcon';
import { produce } from 'immer';
import { useGCPConnection } from '../context/GCPConnectionContext';
import { RadarIcon } from './icons/RadarIcon';

const CHAT_STORAGE_KEY = 'vibe_devops_chat_history';

const initialMessage: ChatMessage = {
  id: 'init-1',
  role: 'model',
  text: 'Hello! I am Vibe, your DevOps assistant. I can help you list tasks (e.g., "list my inprogress tasks"), query your GCP resources, or answer questions. How can I help?',
  timestamp: new Date().toISOString(),
};

// Memoized tool icons mapping
const TOOL_ICONS: Record<string, React.FC<React.SVGProps<SVGSVGElement>>> = {
  discover_gcp_resources: RadarIcon,
  task_manager: TerminalIcon,
  canvas_query: RadarIcon,
  web_search: TerminalIcon,
};

/**
 * Memoized ThinkingBubble component
 */
const ThinkingBubble: React.FC<{ thought: string }> = memo(({ thought }) => (
  <div className="flex items-start space-x-2 text-xs text-gray-400 my-2">
    <CogIcon className="w-4 h-4 flex-shrink-0 animate-spin" />
    <p className="italic">{thought}</p>
  </div>
));

ThinkingBubble.displayName = 'ThinkingBubble';

/**
 * Memoized ToolCallBubble component
 */
const ToolCallBubble: React.FC<{ toolName: string; toolInput: string }> = memo(({ toolName, toolInput }) => {
  const ToolIcon = useMemo(() => TOOL_ICONS[toolName] || TerminalIcon, [toolName]);
  
  return (
    <div className="my-2 text-xs text-gray-400">
      <div className="flex items-center space-x-2">
        <ToolIcon className="w-4 h-4 flex-shrink-0" />
        <p>Using tool: <span className="font-semibold text-gray-300">{toolName}</span></p>
      </div>
      <pre className="mt-1 p-2 bg-gray-900 rounded-md text-gray-300 font-mono text-[11px] max-h-32 overflow-auto">
        {toolInput}
      </pre>
    </div>
  );
});

ToolCallBubble.displayName = 'ToolCallBubble';

/**
 * Memoized ModelMessage component
 */
const ModelMessage: React.FC<{ message: ChatMessage }> = memo(({ message }) => {
  // Memoize whether message is still loading
  const isLoading = useMemo(() => 
    !message.text && !message.steps?.some(s => s.type === 'final_answer'),
    [message.text, message.steps]
  );

  return (
    <div className="flex justify-start">
      <div className="max-w-xs md:max-w-sm lg:max-w-lg p-3 rounded-lg bg-gray-700 text-gray-200">
        {message.steps?.map((step, i) => {
          if (step.type === 'thinking') return <ThinkingBubble key={i} thought={step.thought} />;
          if (step.type === 'tool_call') return <ToolCallBubble key={i} toolName={step.toolName} toolInput={step.toolInput} />;
          return null;
        })}
        {message.text && (
          <p className="text-sm" style={{ whiteSpace: 'pre-wrap' }}>{message.text}</p>
        )}
        {isLoading && <LoadingDots />}
      </div>
    </div>
  );
}, (prev, next) => {
  // Custom comparison for efficient re-renders
  return (
    prev.message.id === next.message.id &&
    prev.message.text === next.message.text &&
    prev.message.steps?.length === next.message.steps?.length
  );
});

ModelMessage.displayName = 'ModelMessage';

/**
 * Memoized loading dots animation
 */
const LoadingDots: React.FC = memo(() => (
  <div className="flex items-center space-x-2">
    <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse"></div>
    <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse delay-75"></div>
    <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse delay-150"></div>
  </div>
));

LoadingDots.displayName = 'LoadingDots';

/**
 * Memoized message item
 */
interface MessageItemProps {
  message: ChatMessage;
  formatTimestamp: (ts: string) => string;
}

const MessageItem: React.FC<MessageItemProps> = memo(({ message, formatTimestamp }) => (
  <div className={`flex flex-col ${message.role === 'user' ? 'items-end' : 'items-start'}`}>
    {message.role === 'user' ? (
      <div className="max-w-xs md:max-w-sm lg:max-w-md p-3 rounded-lg bg-blue-600 text-white">
        <p className="text-sm" style={{ whiteSpace: 'pre-wrap' }}>{message.text}</p>
      </div>
    ) : (
      <ModelMessage message={message} />
    )}
    <span className="text-xs text-gray-500 mt-1 px-1">{formatTimestamp(message.timestamp)}</span>
  </div>
));

MessageItem.displayName = 'MessageItem';

/**
 * Main ChatPanel component with optimizations
 */
const ChatPanel: React.FC = () => {
  const { hasGCPAccess } = useGCPConnection();
  
  // Memoize initial state loader
  const loadInitialMessages = useCallback((): ChatMessage[] => {
    try {
      const storedMessages = localStorage.getItem(CHAT_STORAGE_KEY);
      return storedMessages ? JSON.parse(storedMessages) : [initialMessage];
    } catch (error) {
      console.error("Failed to parse chat history:", error);
      return [initialMessage];
    }
  }, []);

  const [messages, setMessages] = useState<ChatMessage[]>(loadInitialMessages);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const sessionIdRef = useRef(`session-${Date.now()}`);
  
  // Debounced localStorage save
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages));
    }, 500); // Debounce saves
    
    return () => clearTimeout(timeoutId);
  }, [messages]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Memoize timestamp formatter
  const formatTimestamp = useCallback((isoString: string) => {
    return new Date(isoString).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }, []);

  // Optimized send handler
  const handleSend = useCallback(async () => {
    if (input.trim() === '' || isLoading) return;

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      text: input,
      timestamp: new Date().toISOString(),
    };
    
    const modelMessageId = `model-${Date.now()}`;
    
    // Update state in a single batch
    setMessages(prev => [
      ...prev,
      userMessage,
      { id: modelMessageId, role: 'model', steps: [], timestamp: new Date().toISOString() }
    ]);
    setInput('');
    setIsLoading(true);

    try {
      await chatApi.streamMessage(
        {
          message: input,
          session_id: sessionIdRef.current,
          history: []
        },
        (chunk: ModelStep) => {
          setMessages(currentMessages => produce(currentMessages, draft => {
            const messageToUpdate = draft.find(m => m.id === modelMessageId);
            if (messageToUpdate) {
              if (!messageToUpdate.steps) messageToUpdate.steps = [];
              messageToUpdate.steps.push(chunk);
              if (chunk.type === 'final_answer') {
                messageToUpdate.text = chunk.text;
              }
            }
          }));
        }
      );
    } catch (error) {
      console.error('Error streaming chat response:', error);
      setMessages(currentMessages => produce(currentMessages, draft => {
        const messageToUpdate = draft.find(m => m.id === modelMessageId);
        if (messageToUpdate) {
          messageToUpdate.text = `Sorry, I encountered an error: ${error instanceof Error ? error.message : 'Unknown error'}`;
        }
      }));
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading]);

  // Handle input change
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value);
  }, []);

  // Handle key press
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  }, [handleSend]);

  // Memoize GCP status display
  const gcpStatusDisplay = useMemo(() => (
    hasGCPAccess ? (
      <span className="text-green-400">Connected</span>
    ) : (
      <span className="text-yellow-400">Not Connected</span>
    )
  ), [hasGCPAccess]);

  return (
    <div className="flex flex-col h-full bg-gray-800 text-gray-100">
      <div className="flex-1 p-4 overflow-y-auto">
        <div className="space-y-4">
          {messages.map((msg) => (
            <MessageItem 
              key={msg.id} 
              message={msg} 
              formatTimestamp={formatTimestamp}
            />
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>
      <div className="p-4 border-t border-gray-700">
        <div className="flex items-center bg-gray-700 rounded-lg">
          <input
            type="text"
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="Ask Vibe anything..."
            className="flex-1 p-3 bg-transparent border-none rounded-lg focus:ring-0 text-sm"
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={isLoading}
            className="p-3 text-gray-400 hover:text-blue-500 disabled:text-gray-600 transition-colors"
          >
            <PaperAirplaneIcon className="w-5 h-5" />
          </button>
        </div>
        <div className="text-xs text-center text-gray-500 pt-2">
          Agent: <span className="text-green-400">Backend Connected</span>
          <span className="mx-2">|</span>
          GCP: {gcpStatusDisplay}
        </div>
      </div>
    </div>
  );
};

export default memo(ChatPanel);
