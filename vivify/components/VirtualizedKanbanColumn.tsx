import React, { memo, useMemo, useCallback, useRef } from 'react';
import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { useVirtualizer } from '@tanstack/react-virtual';
import TaskCard from './TaskCard';
import { Task, TaskStatus } from '../types';
import { STATUS_CONFIG } from '../constants';

interface VirtualizedKanbanColumnProps {
  status: TaskStatus;
  tasks: Task[];
  onCardClick: (task: Task) => void;
  /** Enable virtualization only for large lists (default: 20 items) */
  virtualizationThreshold?: number;
}

// Estimated row height for virtualization
const ESTIMATED_TASK_HEIGHT = 120;
const TASK_GAP = 8;

/**
 * Virtualized Kanban Column
 * Uses @tanstack/react-virtual for efficient rendering of large task lists
 * Falls back to regular rendering for small lists
 */
const VirtualizedKanbanColumn: React.FC<VirtualizedKanbanColumnProps> = memo(({
  status,
  tasks,
  onCardClick,
  virtualizationThreshold = 20,
}) => {
  const { setNodeRef, isOver } = useDroppable({ id: status });
  const parentRef = useRef<HTMLDivElement>(null);
  
  // Memoize config lookup
  const { label, color } = useMemo(() => STATUS_CONFIG[status], [status]);

  // Memoize task IDs for SortableContext
  const taskIds = useMemo(() => tasks.map(t => t.id), [tasks]);

  // Memoize task count
  const taskCount = useMemo(() => tasks.length, [tasks.length]);

  // Determine if we should use virtualization
  const useVirtualization = tasks.length > virtualizationThreshold;

  // Setup virtualizer
  const virtualizer = useVirtualizer({
    count: tasks.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ESTIMATED_TASK_HEIGHT + TASK_GAP,
    overscan: 5, // Render 5 extra items outside viewport for smoother scrolling
  });

  // Create stable click handlers
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
      {/* Column Header */}
      <ColumnHeader label={label} color={color} count={taskCount} />
      
      {/* Task List with optional virtualization */}
      <div 
        ref={parentRef}
        className="flex-1 p-2 overflow-y-auto"
      >
        <SortableContext items={taskIds} strategy={verticalListSortingStrategy}>
          {useVirtualization ? (
            // Virtualized rendering for large lists
            <div
              style={{
                height: `${virtualizer.getTotalSize()}px`,
                width: '100%',
                position: 'relative',
              }}
            >
              {virtualizer.getVirtualItems().map((virtualRow) => {
                const task = tasks[virtualRow.index];
                return (
                  <div
                    key={task.id}
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      height: `${virtualRow.size - TASK_GAP}px`,
                      transform: `translateY(${virtualRow.start}px)`,
                      paddingBottom: `${TASK_GAP}px`,
                    }}
                  >
                    <TaskCard
                      task={task}
                      onClick={createClickHandler(task)}
                    />
                  </div>
                );
              })}
            </div>
          ) : (
            // Regular rendering for small lists
            <div className="space-y-2">
              {tasks.map((task) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  onClick={createClickHandler(task)}
                />
              ))}
            </div>
          )}
        </SortableContext>
      </div>
      
      {/* Virtualization indicator (dev mode) */}
      {process.env.NODE_ENV === 'development' && useVirtualization && (
        <div className="px-2 py-1 text-xs text-gray-500 border-t border-gray-700">
          📜 Virtual: {virtualizer.getVirtualItems().length}/{tasks.length} rendered
        </div>
      )}
    </div>
  );
}, (prevProps, nextProps) => {
  // Custom comparison
  if (prevProps.status !== nextProps.status) return false;
  if (prevProps.tasks.length !== nextProps.tasks.length) return false;
  if (prevProps.onCardClick !== nextProps.onCardClick) return false;
  if (prevProps.virtualizationThreshold !== nextProps.virtualizationThreshold) return false;
  
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

VirtualizedKanbanColumn.displayName = 'VirtualizedKanbanColumn';

/**
 * Memoized Column Header
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

export default VirtualizedKanbanColumn;

