import { useState, useEffect, useRef, useCallback } from 'react';
import { produce } from 'immer';
import { applyPatch } from '../utils/jsonPatch';
import { Task, TaskStatus, JsonPatchOperation } from '../types';

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

const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000';

export const useTaskWebSocket = (projectId: string) => {
  // FIX: The state shape was incorrect. The JSON patches expect a root object with a `tasks` property.
  const [state, setState] = useState<{ tasks: Record<string, Task> }>({ tasks: {} });
  const [isLoading, setIsLoading] = useState(true);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const retryAttempt = useRef(0);
  const pollIntervalRef = useRef<any>(null);

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

  const fetchTasks = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/tasks`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      
      // Convert array to Record<string, Task>
      const tasksRecord: Record<string, Task> = {};
      data.tasks.forEach((task: Task) => {
        tasksRecord[task.id] = task;
      });
      
      // Apply as a patch
      const patch: JsonPatchOperation[] = [{ op: 'replace', path: '/tasks', value: tasksRecord }];
      applyPatches(patch);
      
      setIsConnected(true);
      setIsLoading(false);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch tasks:', err);
      setError(err instanceof Error ? err : new Error('Failed to fetch tasks'));
      setIsLoading(false);
    }
  }, [applyPatches]);

  const connect = useCallback(() => {
    console.log(`Fetching tasks from backend API...`);
    setIsConnected(false);

    // Initial fetch
    fetchTasks();

    // Poll for updates every 5 seconds
    pollIntervalRef.current = setInterval(() => {
      fetchTasks();
    }, 5000);
  }, [fetchTasks]);

  useEffect(() => {
    connect();
    return () => {
      // Cleanup: clear polling interval
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [connect]);
  
  const updateTaskStatus = useCallback(async (taskId: string, newStatus: TaskStatus) => {
    try {
      // Update via API
      const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status: newStatus }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      // Immediately fetch fresh data
      await fetchTasks();
    } catch (err) {
      console.error('Failed to update task:', err);
      setError(err instanceof Error ? err : new Error('Failed to update task'));
    }
  }, [fetchTasks]);

  return { tasks: state.tasks, isLoading, isConnected, error, updateTaskStatus };
};
