import React, { memo, useMemo, useCallback } from 'react';
import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import TaskCard from './TaskCard';
import { Task, TaskStatus } from '../types';
import { STATUS_CONFIG } from '../constants';

interface KanbanColumnProps {
  status: TaskStatus;
  tasks: Task[];
  onCardClick: (task: Task) => void;
}

/**
 * Memoized KanbanColumn component
 * Uses virtualization-ready structure for large task lists
 */
const KanbanColumn: React.FC<KanbanColumnProps> = memo(({ status, tasks, onCardClick }) => {
  const { setNodeRef, isOver } = useDroppable({ id: status });
  
  // Memoize config lookup
  const { label, color } = useMemo(() => STATUS_CONFIG[status], [status]);

  // Memoize task IDs for SortableContext
  const taskIds = useMemo(() => tasks.map(t => t.id), [tasks]);

  // Memoize task count
  const taskCount = useMemo(() => tasks.length, [tasks.length]);

  // Create stable click handlers for each task
  const createClickHandler = useCallback((task: Task) => () => {
    onCardClick(task);
  }, [onCardClick]);

  // Memoize column class name
  const columnClassName = useMemo(() => 
    `flex flex-col w-72 md:w-80 lg:w-96 flex-shrink-0 rounded-lg bg-gray-800 shadow-lg h-full transition-colors duration-200 ${isOver ? 'bg-gray-700' : ''}`,
    [isOver]
  );

  return (
    <div
      ref={setNodeRef}
      className={columnClassName}
    >
      {/* Column Header - Memoized internally */}
      <ColumnHeader label={label} color={color} count={taskCount} />
      
      {/* Task List */}
      <div className="flex-1 p-2 overflow-y-auto space-y-2">
        <SortableContext items={taskIds} strategy={verticalListSortingStrategy}>
          {tasks.map((task) => (
            <TaskCard 
              key={task.id} 
              task={task} 
              onClick={createClickHandler(task)} 
            />
          ))}
        </SortableContext>
      </div>
    </div>
  );
}, (prevProps, nextProps) => {
  // Custom comparison - check if tasks array actually changed
  if (prevProps.status !== nextProps.status) return false;
  if (prevProps.tasks.length !== nextProps.tasks.length) return false;
  if (prevProps.onCardClick !== nextProps.onCardClick) return false;
  
  // Deep compare task IDs and update times
  for (let i = 0; i < prevProps.tasks.length; i++) {
    const prev = prevProps.tasks[i];
    const next = nextProps.tasks[i];
    if (prev.id !== next.id || prev.updated_at !== next.updated_at || prev.status !== next.status) {
      return false;
    }
  }
  
  return true;
});

KanbanColumn.displayName = 'KanbanColumn';

/**
 * Memoized Column Header component
 */
interface ColumnHeaderProps {
  label: string;
  color: string;
  count: number;
}

const ColumnHeader: React.FC<ColumnHeaderProps> = memo(({ label, color, count }) => (
  <div className="flex items-center justify-between p-4 border-b border-gray-700">
    <div className="flex items-center space-x-2">
      <span className={`w-3 h-3 rounded-full ${color}`}></span>
      <h2 className="font-bold text-white">{label}</h2>
    </div>
    <span className="text-sm font-medium text-gray-400 bg-gray-700 rounded-full px-2 py-1">
      {count}
    </span>
  </div>
));

ColumnHeader.displayName = 'ColumnHeader';

export default KanbanColumn;
