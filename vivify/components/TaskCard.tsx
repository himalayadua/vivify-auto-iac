import React, { memo, useMemo, useCallback } from 'react';
import { useDraggable } from '@dnd-kit/core';
import { CSS } from '@dnd-kit/utilities';
import { Task, TaskStatus } from '../types';
import { STATUS_CONFIG } from '../constants';

interface TaskCardProps {
  task: Task;
  onClick: () => void;
}

/**
 * Memoized TaskCard component
 * Only re-renders when task data or onClick changes
 */
const TaskCard: React.FC<TaskCardProps> = memo(({ task, onClick }) => {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: task.id,
    data: { task },
  });

  // Memoize style calculation to prevent recalculation on every render
  const style = useMemo(() => ({
    transform: CSS.Translate.toString(transform),
    zIndex: isDragging ? 100 : 'auto' as const,
    opacity: isDragging ? 0.8 : 1,
  }), [transform, isDragging]);
  
  // Memoize status color lookup
  const statusColor = useMemo(() => 
    STATUS_CONFIG[task.status as TaskStatus]?.color || 'bg-gray-500',
    [task.status]
  );

  // Memoize formatted date to avoid recalculation
  const formattedDate = useMemo(() => 
    new Date(task.updated_at).toLocaleDateString(),
    [task.updated_at]
  );

  // Memoize description to prevent unnecessary string operations
  const description = useMemo(() => 
    task.description || 'No description provided.',
    [task.description]
  );

  // Stable onClick handler
  const handleClick = useCallback(() => {
    onClick();
  }, [onClick]);

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      onClick={handleClick}
      className="p-4 bg-gray-700 rounded-lg shadow-md cursor-pointer hover:bg-gray-600 transition-all duration-200 border-l-4 border-transparent hover:border-blue-500"
    >
      <div className="flex justify-between items-start">
        <h3 className="font-bold text-white mb-2">{task.title}</h3>
        <span className={`w-2.5 h-2.5 rounded-full ${statusColor} mt-1 flex-shrink-0`}></span>
      </div>
      
      <p className="text-sm text-gray-400 line-clamp-3">
        {description}
      </p>
      <div className="text-xs text-gray-500 mt-3 pt-2 border-t border-gray-600">
        Updated: {formattedDate}
      </div>
    </div>
  );
}, (prevProps, nextProps) => {
  // Custom comparison function for memo
  // Only re-render if task data actually changed
  return (
    prevProps.task.id === nextProps.task.id &&
    prevProps.task.title === nextProps.task.title &&
    prevProps.task.description === nextProps.task.description &&
    prevProps.task.status === nextProps.task.status &&
    prevProps.task.updated_at === nextProps.task.updated_at &&
    prevProps.onClick === nextProps.onClick
  );
});

TaskCard.displayName = 'TaskCard';

export default TaskCard;
