import React, { createContext, useContext, useMemo, useCallback, useRef } from 'react';
import { useTaskWebSocket } from '../hooks/useTaskWebSocket';
import { Task, TaskStatus } from '../types';
import { COLUMN_ORDER } from '../constants';

type GroupedTasks = Record<TaskStatus, Task[]>;

interface KanbanContextType {
  tasksById: Record<string, Task>;
  groupedTasks: GroupedTasks;
  tasks: Task[];
  isLoading: boolean;
  isConnected: boolean;
  error: Error | null;
  updateTaskStatus: (taskId: string, newStatus: TaskStatus) => void;
  batchUpdateTaskStatus: (updates: Array<{ taskId: string; newStatus: TaskStatus }>) => void;
  setSelectedTask: (task: Task | null) => void;
  getTaskById: (taskId: string) => Task | undefined;
  getTasksByStatus: (status: TaskStatus) => Task[];
}

const KanbanContext = createContext<KanbanContextType | undefined>(undefined);

export const KanbanProvider: React.FC<{
  children: React.ReactNode;
  setSelectedTask: (task: Task | null) => void;
}> = ({ children, setSelectedTask }) => {
  const { 
    tasks: tasksById, 
    isLoading, 
    isConnected, 
    error, 
    updateTaskStatus: wsUpdateTaskStatus,
    batchUpdateTaskStatus: wsBatchUpdateTaskStatus 
  } = useTaskWebSocket('mock_project_id');

  // Memoize sorted tasks array
  const tasks = useMemo(() => {
    return Object.values(tasksById).sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  }, [tasksById]);

  // Memoize grouped tasks with stable reference
  const groupedTasks = useMemo(() => {
    // Initialize with empty arrays for all statuses
    const initialGroups: GroupedTasks = {} as GroupedTasks;
    COLUMN_ORDER.forEach(status => {
      initialGroups[status] = [];
    });

    // Group tasks by status
    return tasks.reduce((acc, task) => {
      if (acc[task.status]) {
        acc[task.status].push(task);
      }
      return acc;
    }, initialGroups);
  }, [tasks]);
  
  // Memoize task status update function
  const updateTaskStatus = useCallback((taskId: string, newStatus: TaskStatus) => {
    console.log(`Updating task ${taskId} to status ${newStatus}`);
    wsUpdateTaskStatus(taskId, newStatus);
  }, [wsUpdateTaskStatus]);

  // Batch update for multiple tasks (optimized for bulk operations)
  const batchUpdateTaskStatus = useCallback((
    updates: Array<{ taskId: string; newStatus: TaskStatus }>
  ) => {
    console.log(`Batch updating ${updates.length} tasks`);
    wsBatchUpdateTaskStatus(updates);
  }, [wsBatchUpdateTaskStatus]);

  // Memoized task lookup by ID
  const getTaskById = useCallback((taskId: string) => {
    return tasksById[taskId];
  }, [tasksById]);

  // Memoized tasks by status lookup
  const getTasksByStatus = useCallback((status: TaskStatus) => {
    return groupedTasks[status] || [];
  }, [groupedTasks]);

  // Memoize the entire context value
  const value = useMemo(() => ({
    tasksById,
    groupedTasks,
    tasks,
    isLoading,
    isConnected,
    error,
    updateTaskStatus,
    batchUpdateTaskStatus,
    setSelectedTask,
    getTaskById,
    getTasksByStatus,
  }), [
    tasksById,
    groupedTasks,
    tasks,
    isLoading,
    isConnected,
    error,
    updateTaskStatus,
    batchUpdateTaskStatus,
    setSelectedTask,
    getTaskById,
    getTasksByStatus,
  ]);

  return <KanbanContext.Provider value={value}>{children}</KanbanContext.Provider>;
};

export const useKanban = (): KanbanContextType => {
  const context = useContext(KanbanContext);
  if (context === undefined) {
    throw new Error('useKanban must be used within a KanbanProvider');
  }
  return context;
};

/**
 * Selector hook for accessing specific task data
 * Uses reference equality to prevent unnecessary re-renders
 */
export const useTask = (taskId: string): Task | undefined => {
  const { tasksById } = useKanban();
  return useMemo(() => tasksById[taskId], [tasksById, taskId]);
};

/**
 * Selector hook for accessing tasks by status
 */
export const useTasksByStatus = (status: TaskStatus): Task[] => {
  const { groupedTasks } = useKanban();
  return useMemo(() => groupedTasks[status] || [], [groupedTasks, status]);
};
