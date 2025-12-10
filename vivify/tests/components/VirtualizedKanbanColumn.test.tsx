/**
 * Tests for VirtualizedKanbanColumn component
 * Verifies virtual scrolling behavior
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import VirtualizedKanbanColumn from '../../components/VirtualizedKanbanColumn';
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

// Mock @tanstack/react-virtual
jest.mock('@tanstack/react-virtual', () => ({
  useVirtualizer: ({ count }: { count: number }) => ({
    getVirtualItems: () => 
      Array.from({ length: Math.min(count, 10) }, (_, i) => ({
        index: i,
        start: i * 128,
        size: 120,
        key: i,
      })),
    getTotalSize: () => count * 128,
  }),
}));

describe('VirtualizedKanbanColumn', () => {
  const createTasks = (count: number): Task[] => 
    Array.from({ length: count }, (_, i) => ({
      id: `task-${i}`,
      title: `Task ${i}`,
      status: TaskStatus.Todo,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    }));

  const mockOnCardClick = jest.fn();

  beforeEach(() => {
    mockOnCardClick.mockClear();
  });

  it('renders without virtualization for small lists', () => {
    const tasks = createTasks(5);
    
    render(
      <VirtualizedKanbanColumn
        status={TaskStatus.Todo}
        tasks={tasks}
        onCardClick={mockOnCardClick}
        virtualizationThreshold={20}
      />
    );

    // All 5 tasks should be rendered
    expect(screen.getByText('Task 0')).toBeInTheDocument();
    expect(screen.getByText('Task 4')).toBeInTheDocument();
  });

  it('uses virtualization for large lists', () => {
    const tasks = createTasks(50);
    
    render(
      <VirtualizedKanbanColumn
        status={TaskStatus.Todo}
        tasks={tasks}
        onCardClick={mockOnCardClick}
        virtualizationThreshold={20}
      />
    );

    // Header should show total count
    expect(screen.getByText('50')).toBeInTheDocument();
    
    // Only virtualized items should be rendered (mocked to 10)
    expect(screen.getByText('Task 0')).toBeInTheDocument();
  });

  it('respects custom virtualization threshold', () => {
    const tasks = createTasks(15);
    
    // With threshold of 10, 15 tasks should use virtualization
    render(
      <VirtualizedKanbanColumn
        status={TaskStatus.Todo}
        tasks={tasks}
        onCardClick={mockOnCardClick}
        virtualizationThreshold={10}
      />
    );

    // Should still render (virtualization is enabled)
    expect(screen.getByText('15')).toBeInTheDocument();
  });

  it('renders correct status header', () => {
    const tasks = createTasks(5);
    
    render(
      <VirtualizedKanbanColumn
        status={TaskStatus.InProgress}
        tasks={tasks}
        onCardClick={mockOnCardClick}
      />
    );

    expect(screen.getByText('In Progress')).toBeInTheDocument();
  });
});

describe('VirtualizedKanbanColumn Performance', () => {
  it('only renders visible items for large lists', () => {
    const tasks = Array.from({ length: 100 }, (_, i) => ({
      id: `task-${i}`,
      title: `Task ${i}`,
      status: TaskStatus.Todo,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    }));

    const { container } = render(
      <VirtualizedKanbanColumn
        status={TaskStatus.Todo}
        tasks={tasks}
        onCardClick={jest.fn()}
        virtualizationThreshold={20}
      />
    );

    // Should not render all 100 task cards
    // Our mock renders max 10 virtual items
    const taskCards = container.querySelectorAll('[class*="bg-gray-700"]');
    expect(taskCards.length).toBeLessThan(100);
  });
});

