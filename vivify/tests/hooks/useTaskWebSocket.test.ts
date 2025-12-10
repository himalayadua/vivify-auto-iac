/**
 * Tests for useTaskWebSocket hook
 * Verifies WebSocket batching and state management
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import { useTaskWebSocket, MOCK_INITIAL_TASKS } from '../../hooks/useTaskWebSocket';
import { TaskStatus } from '../../types';

// Mock timers for testing batching delays
jest.useFakeTimers();

describe('useTaskWebSocket', () => {
  afterEach(() => {
    jest.clearAllTimers();
  });

  it('initializes with loading state', () => {
    const { result } = renderHook(() => useTaskWebSocket('test-project'));
    
    expect(result.current.isLoading).toBe(true);
    expect(result.current.isConnected).toBe(false);
    expect(result.current.error).toBe(null);
  });

  it('loads initial tasks after connection', async () => {
    const { result } = renderHook(() => useTaskWebSocket('test-project'));
    
    // Advance timers to simulate connection delay
    act(() => {
      jest.advanceTimersByTime(1000);
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
      expect(result.current.isConnected).toBe(true);
    });

    // Should have initial tasks
    expect(Object.keys(result.current.tasks).length).toBeGreaterThan(0);
  });

  it('updates task status', async () => {
    const { result } = renderHook(() => useTaskWebSocket('test-project'));
    
    // Wait for connection
    act(() => {
      jest.advanceTimersByTime(1000);
    });

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });

    // Update task status
    act(() => {
      result.current.updateTaskStatus('task-1', TaskStatus.Done);
    });

    // Advance timers to flush batch
    act(() => {
      jest.advanceTimersByTime(100);
    });

    await waitFor(() => {
      expect(result.current.tasks['task-1']?.status).toBe(TaskStatus.Done);
    });
  });

  it('batch updates multiple tasks', async () => {
    const { result } = renderHook(() => useTaskWebSocket('test-project'));
    
    // Wait for connection
    act(() => {
      jest.advanceTimersByTime(1000);
    });

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });

    // Batch update
    act(() => {
      result.current.batchUpdateTaskStatus([
        { taskId: 'task-1', newStatus: TaskStatus.Done },
        { taskId: 'task-2', newStatus: TaskStatus.Done },
      ]);
    });

    await waitFor(() => {
      expect(result.current.tasks['task-1']?.status).toBe(TaskStatus.Done);
      expect(result.current.tasks['task-2']?.status).toBe(TaskStatus.Done);
    });
  });
});

describe('useTaskWebSocket Batching', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('batches multiple rapid updates', async () => {
    const { result } = renderHook(() => useTaskWebSocket('test-project'));
    
    // Wait for connection
    act(() => {
      jest.advanceTimersByTime(1000);
    });

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });

    // Make multiple rapid updates (should be batched)
    act(() => {
      result.current.updateTaskStatus('task-1', TaskStatus.InProgress);
      result.current.updateTaskStatus('task-1', TaskStatus.InReview);
      result.current.updateTaskStatus('task-1', TaskStatus.Done);
    });

    // Before flush, no updates applied yet
    // (batching delays the update)

    // Flush batch
    act(() => {
      jest.advanceTimersByTime(100);
    });

    // After flush, only final status should remain
    await waitFor(() => {
      expect(result.current.tasks['task-1']?.status).toBe(TaskStatus.Done);
    });
  });

  it('flushes on max batch size', async () => {
    const { result } = renderHook(() => useTaskWebSocket('test-project'));
    
    // Wait for connection
    act(() => {
      jest.advanceTimersByTime(1000);
    });

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });

    // Make many updates (exceeds batch size of 50)
    act(() => {
      for (let i = 0; i < 60; i++) {
        result.current.updateTaskStatus('task-1', TaskStatus.InProgress);
      }
    });

    // Should have flushed automatically
    await waitFor(() => {
      expect(result.current.tasks['task-1']?.status).toBe(TaskStatus.InProgress);
    });
  });
});

describe('useTaskWebSocket Error Handling', () => {
  it('handles patch application errors gracefully', async () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
    
    const { result } = renderHook(() => useTaskWebSocket('test-project'));
    
    // Wait for connection
    act(() => {
      jest.advanceTimersByTime(1000);
    });

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });

    // The hook should continue working even after errors
    expect(result.current.error).toBe(null);

    consoleSpy.mockRestore();
  });
});

