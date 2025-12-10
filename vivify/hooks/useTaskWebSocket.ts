import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { produce } from 'immer';
import { applyPatch } from '../utils/jsonPatch';
import { Task, TaskStatus, JsonPatchOperation } from '../types';

// Configuration for WebSocket batching
const BATCH_CONFIG = {
  maxBatchSize: 50,
  maxBatchDelayMs: 100,
  enabled: true,
};

// Mock data to simulate server responses
export const MOCK_INITIAL_TASKS: Record<string, Task> = {
  'task-1': {
    id: 'task-1',
    title: 'Setup CI/CD Pipeline',
    description: 'Configure GitHub Actions for automated testing and deployment.',
    status: TaskStatus.Todo,
    created_at: '2023-10-26T10:00:00Z',
    updated_at: '2023-10-26T10:00:00Z',
    subtasks: [
      { id: 'sub-1', title: 'Configure SonarCloud analysis', status: 'pending', task_id: 'task-1' },
      { id: 'sub-2', title: 'Set up deployment to staging', status: 'completed', task_id: 'task-1' }
    ]
  },
  'task-2': {
    id: 'task-2',
    title: 'Develop User Authentication',
    description: 'Implement JWT-based authentication for the main API.',
    status: TaskStatus.InProgress,
    created_at: '2023-10-25T11:00:00Z',
    updated_at: '2023-10-25T12:30:00Z',
    metadata: {
      assignee: 'Alice',
      priority: 'High',
      sprint: 'Sprint 3'
    }
  },
  'task-3': { id: 'task-3', title: 'Design Database Schema', description: 'Finalize the PostgreSQL schema for all services.', status: TaskStatus.Done, created_at: '2023-10-24T09:00:00Z', updated_at: '2023-10-24T15:00:00Z' },
  'task-4': { id: 'task-4', title: 'Code Review for Feature X', description: 'Review pull request #123 for the new notifications feature.', status: TaskStatus.InReview, created_at: '2023-10-26T14:00:00Z', updated_at: '2023-10-26T14:00:00Z' },
  'task-5': { id: 'task-5', title: 'Fix Login Page CSS Bug', description: 'The login button is misaligned on mobile devices.', status: TaskStatus.InProgress, created_at: '2023-10-26T15:00:00Z', updated_at: '2023-10-26T15:00:00Z' },
  'task-6': { id: 'task-6', title: 'Deploy Staging Environment', description: 'Push the latest build to the staging server for QA testing.', status: TaskStatus.Todo, created_at: '2023-10-26T16:00:00Z', updated_at: '2023-10-26T16:00:00Z' },
};

interface PendingUpdate {
  taskId: string;
  field: string;
  value: any;
  timestamp: number;
}

interface WebSocketState {
  tasks: Record<string, Task>;
}

export const useTaskWebSocket = (projectId: string) => {
  const [state, setState] = useState<WebSocketState>({ tasks: {} });
  const [isLoading, setIsLoading] = useState(true);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  
  // Refs for batching
  const pendingUpdates = useRef<PendingUpdate[]>([]);
  const batchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mockTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Optimized patch application with batching
  const applyPatches = useCallback((patches: JsonPatchOperation[]) => {
    try {
      setState(currentState => {
        const nextState = produce(currentState, draft => {
          applyPatch(draft, patches);
        });
        return nextState;
      });
    } catch (e) {
      console.error('Failed to apply patch:', e);
      setError(e instanceof Error ? e : new Error('Failed to apply patch'));
    }
  }, []);

  // Flush pending updates as a batch
  const flushPendingUpdates = useCallback(() => {
    if (pendingUpdates.current.length === 0) return;

    // Optimize: merge updates for the same task/field
    const mergedUpdates = new Map<string, PendingUpdate>();
    for (const update of pendingUpdates.current) {
      const key = `${update.taskId}:${update.field}`;
      // Keep only the latest update for each task/field combination
      if (!mergedUpdates.has(key) || mergedUpdates.get(key)!.timestamp < update.timestamp) {
        mergedUpdates.set(key, update);
      }
    }

    // Convert to patches
    const patches: JsonPatchOperation[] = Array.from(mergedUpdates.values()).flatMap(update => [
      { op: 'replace' as const, path: `/tasks/${update.taskId}/${update.field}`, value: update.value },
    ]);

    // Add updated_at for each unique task
    const uniqueTaskIds = new Set(Array.from(mergedUpdates.values()).map(u => u.taskId));
    for (const taskId of uniqueTaskIds) {
      patches.push({
        op: 'replace' as const,
        path: `/tasks/${taskId}/updated_at`,
        value: new Date().toISOString()
      });
    }

    // Apply all patches at once
    applyPatches(patches);

    // Clear pending updates
    pendingUpdates.current = [];
    
    console.log(`Flushed ${patches.length} batched updates`);
  }, [applyPatches]);

  // Schedule batch flush
  const scheduleBatchFlush = useCallback(() => {
    if (!BATCH_CONFIG.enabled) {
      flushPendingUpdates();
      return;
    }

    // Clear existing timeout
    if (batchTimeoutRef.current) {
      clearTimeout(batchTimeoutRef.current);
    }

    // Check if we should flush immediately (max batch size reached)
    if (pendingUpdates.current.length >= BATCH_CONFIG.maxBatchSize) {
      flushPendingUpdates();
      return;
    }

    // Schedule delayed flush
    batchTimeoutRef.current = setTimeout(() => {
      flushPendingUpdates();
    }, BATCH_CONFIG.maxBatchDelayMs);
  }, [flushPendingUpdates]);

  // Add update to batch
  const queueUpdate = useCallback((taskId: string, field: string, value: any) => {
    pendingUpdates.current.push({
      taskId,
      field,
      value,
      timestamp: Date.now()
    });
    scheduleBatchFlush();
  }, [scheduleBatchFlush]);

  // Connect to WebSocket (simulated)
  const connect = useCallback(() => {
    console.log(`Connecting to ws://localhost:8080/api/tasks/stream/ws?project_id=${projectId}`);
    setIsConnected(false);

    mockTimeoutRef.current = setTimeout(() => {
      console.log('WebSocket connection established.');
      setIsConnected(true);
      setIsLoading(false);
      setError(null);

      // Initial snapshot
      const initialPatch: JsonPatchOperation[] = [
        { op: 'replace', path: '/tasks', value: MOCK_INITIAL_TASKS }
      ];
      applyPatches(initialPatch);
    }, 1000);
  }, [projectId, applyPatches]);

  useEffect(() => {
    connect();
    return () => {
      if (mockTimeoutRef.current) {
        clearTimeout(mockTimeoutRef.current);
      }
      if (batchTimeoutRef.current) {
        clearTimeout(batchTimeoutRef.current);
      }
      // Flush any remaining updates on unmount
      flushPendingUpdates();
    };
  }, [connect, flushPendingUpdates]);
  
  // Single task status update (batched)
  const updateTaskStatus = useCallback((taskId: string, newStatus: TaskStatus) => {
    queueUpdate(taskId, 'status', newStatus);
  }, [queueUpdate]);

  // Batch update multiple tasks at once
  const batchUpdateTaskStatus = useCallback((
    updates: Array<{ taskId: string; newStatus: TaskStatus }>
  ) => {
    for (const { taskId, newStatus } of updates) {
      pendingUpdates.current.push({
        taskId,
        field: 'status',
        value: newStatus,
        timestamp: Date.now()
      });
    }
    // Force immediate flush for explicit batch updates
    flushPendingUpdates();
  }, [flushPendingUpdates]);

  // Memoize return value to prevent unnecessary re-renders
  return useMemo(() => ({
    tasks: state.tasks,
    isLoading,
    isConnected,
    error,
    updateTaskStatus,
    batchUpdateTaskStatus
  }), [state.tasks, isLoading, isConnected, error, updateTaskStatus, batchUpdateTaskStatus]);
};
