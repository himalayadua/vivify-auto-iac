import React, { memo, useMemo, useCallback } from 'react';
import {
  DndContext,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
  closestCenter,
} from '@dnd-kit/core';
import { useKanban } from '../context/KanbanContext';
import VirtualizedKanbanColumn from './VirtualizedKanbanColumn';
import { Task, TaskStatus } from '../types';
import { COLUMN_ORDER } from '../constants';

interface KanbanBoardProps {
  onCardClick: (task: Task) => void;
  /** Enable virtualization for columns with more than this many tasks */
  virtualizationThreshold?: number;
}

/**
 * Optimized Kanban Board with virtualization support
 */
const KanbanBoard: React.FC<KanbanBoardProps> = memo(({ 
  onCardClick,
  virtualizationThreshold = 20 
}) => {
  const { groupedTasks, isLoading, updateTaskStatus } = useKanban();

  // Memoize sensors configuration
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  // Memoize drag end handler
  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const taskId = active.id as string;
      const newStatus = over.id as TaskStatus;
      
      const currentStatus = (active.data.current?.task as Task)?.status;

      if (currentStatus && newStatus !== currentStatus) {
        updateTaskStatus(taskId, newStatus);
      }
    }
  }, [updateTaskStatus]);

  // Memoize the column components to prevent unnecessary re-renders
  const columns = useMemo(() => (
    COLUMN_ORDER.map((status) => (
      <VirtualizedKanbanColumn
        key={status}
        status={status}
        tasks={groupedTasks[status] || []}
        onCardClick={onCardClick}
        virtualizationThreshold={virtualizationThreshold}
      />
    ))
  ), [groupedTasks, onCardClick, virtualizationThreshold]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <DndContext 
      sensors={sensors} 
      collisionDetection={closestCenter} 
      onDragEnd={handleDragEnd}
    >
      <div className="flex h-full p-4 space-x-4 overflow-x-auto bg-gray-900">
        {columns}
      </div>
    </DndContext>
  );
});

KanbanBoard.displayName = 'KanbanBoard';

/**
 * Memoized loading spinner
 */
const LoadingSpinner: React.FC = memo(() => (
  <div className="flex flex-col items-center space-y-4">
    <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
    <p className="text-gray-400">Loading tasks...</p>
  </div>
));

LoadingSpinner.displayName = 'LoadingSpinner';

export default KanbanBoard;
