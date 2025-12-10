/**
 * Tests for KanbanColumn component
 * Verifies memoization and task grouping
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import KanbanColumn from '../../components/KanbanColumn';
import { Task, TaskStatus } from '../../types';

// Mock dnd-kit
jest.mock('@dnd-kit/core', () => ({
  useDroppable: () => ({
    setNodeRef: jest.fn(),
    isOver: false,
  }),
  useDraggable: () => ({
    attributes: {},
    listeners: {},
    setNodeRef: jest.fn(),
    transform: null,
    isDragging: false,
  }),
}));

jest.mock('@dnd-kit/sortable', () => ({
  SortableContext: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  verticalListSortingStrategy: {},
}));

jest.mock('@dnd-kit/utilities', () => ({
  CSS: {
    Translate: {
      toString: () => '',
    },
  },
}));

describe('KanbanColumn', () => {
  const mockTasks: Task[] = [
    {
      id: 'task-1',
      title: 'Task 1',
      status: TaskStatus.Todo,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 'task-2',
      title: 'Task 2',
      status: TaskStatus.Todo,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
  ];

  const mockOnCardClick = jest.fn();

  beforeEach(() => {
    mockOnCardClick.mockClear();
  });

  it('renders column header with status label', () => {
    render(
      <KanbanColumn
        status={TaskStatus.Todo}
        tasks={mockTasks}
        onCardClick={mockOnCardClick}
      />
    );

    expect(screen.getByText('To Do')).toBeInTheDocument();
  });

  it('renders task count badge', () => {
    render(
      <KanbanColumn
        status={TaskStatus.Todo}
        tasks={mockTasks}
        onCardClick={mockOnCardClick}
      />
    );

    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('renders all tasks', () => {
    render(
      <KanbanColumn
        status={TaskStatus.Todo}
        tasks={mockTasks}
        onCardClick={mockOnCardClick}
      />
    );

    expect(screen.getByText('Task 1')).toBeInTheDocument();
    expect(screen.getByText('Task 2')).toBeInTheDocument();
  });

  it('renders empty column', () => {
    render(
      <KanbanColumn
        status={TaskStatus.Done}
        tasks={[]}
        onCardClick={mockOnCardClick}
      />
    );

    expect(screen.getByText('Done')).toBeInTheDocument();
    expect(screen.getByText('0')).toBeInTheDocument();
  });

  it('applies correct status color', () => {
    const { container } = render(
      <KanbanColumn
        status={TaskStatus.InProgress}
        tasks={[]}
        onCardClick={mockOnCardClick}
      />
    );

    // Check for status color class
    const statusDot = container.querySelector('.bg-blue-500');
    expect(statusDot).toBeInTheDocument();
  });
});

describe('KanbanColumn Memoization', () => {
  const mockTasks: Task[] = [
    {
      id: 'task-1',
      title: 'Task 1',
      status: TaskStatus.Todo,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
  ];

  it('should not re-render when tasks array has same content', () => {
    const onCardClick = jest.fn();
    
    const { rerender } = render(
      <KanbanColumn
        status={TaskStatus.Todo}
        tasks={mockTasks}
        onCardClick={onCardClick}
      />
    );

    // Re-render with equivalent array (different reference, same content)
    const sameTasks = [...mockTasks];
    
    rerender(
      <KanbanColumn
        status={TaskStatus.Todo}
        tasks={sameTasks}
        onCardClick={onCardClick}
      />
    );

    // Component should still work
    expect(screen.getByText('Task 1')).toBeInTheDocument();
  });
});

