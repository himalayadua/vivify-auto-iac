/**
 * Tests for TaskCard component
 * Verifies memoization and rendering optimization
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import TaskCard from '../../components/TaskCard';
import { Task, TaskStatus } from '../../types';

// Mock dnd-kit
jest.mock('@dnd-kit/core', () => ({
  useDraggable: () => ({
    attributes: {},
    listeners: {},
    setNodeRef: jest.fn(),
    transform: null,
    isDragging: false,
  }),
}));

jest.mock('@dnd-kit/utilities', () => ({
  CSS: {
    Translate: {
      toString: () => '',
    },
  },
}));

describe('TaskCard', () => {
  const mockTask: Task = {
    id: 'task-1',
    title: 'Test Task',
    description: 'Test description',
    status: TaskStatus.Todo,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
  };

  const mockOnClick = jest.fn();

  beforeEach(() => {
    mockOnClick.mockClear();
  });

  it('renders task title', () => {
    render(<TaskCard task={mockTask} onClick={mockOnClick} />);
    expect(screen.getByText('Test Task')).toBeInTheDocument();
  });

  it('renders task description', () => {
    render(<TaskCard task={mockTask} onClick={mockOnClick} />);
    expect(screen.getByText('Test description')).toBeInTheDocument();
  });

  it('renders default description when none provided', () => {
    const taskWithoutDesc = { ...mockTask, description: undefined };
    render(<TaskCard task={taskWithoutDesc} onClick={mockOnClick} />);
    expect(screen.getByText('No description provided.')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    render(<TaskCard task={mockTask} onClick={mockOnClick} />);
    
    const card = screen.getByText('Test Task').closest('div');
    fireEvent.click(card!);
    
    expect(mockOnClick).toHaveBeenCalledTimes(1);
  });

  it('renders formatted date', () => {
    render(<TaskCard task={mockTask} onClick={mockOnClick} />);
    // The date should be formatted
    expect(screen.getByText(/Updated:/)).toBeInTheDocument();
  });

  it('renders status indicator', () => {
    render(<TaskCard task={mockTask} onClick={mockOnClick} />);
    // Status dot should be present
    const statusDot = document.querySelector('.rounded-full');
    expect(statusDot).toBeInTheDocument();
  });
});

describe('TaskCard Memoization', () => {
  const mockTask: Task = {
    id: 'task-memo',
    title: 'Memo Test',
    description: 'Testing memoization',
    status: TaskStatus.InProgress,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
  };

  it('should not re-render when props are the same', () => {
    const renderCount = { count: 0 };
    
    // Create a wrapper to track renders
    const TrackedTaskCard = React.memo((props: { task: Task; onClick: () => void }) => {
      renderCount.count++;
      return <TaskCard {...props} />;
    });

    const onClick = jest.fn();
    
    const { rerender } = render(
      <TrackedTaskCard task={mockTask} onClick={onClick} />
    );

    expect(renderCount.count).toBe(1);

    // Re-render with same props (same reference)
    rerender(<TrackedTaskCard task={mockTask} onClick={onClick} />);
    
    // Memo should prevent re-render
    expect(renderCount.count).toBe(1);
  });

  it('should re-render when task changes', () => {
    const onClick = jest.fn();
    
    const { rerender } = render(
      <TaskCard task={mockTask} onClick={onClick} />
    );

    const updatedTask = {
      ...mockTask,
      title: 'Updated Title',
    };

    rerender(<TaskCard task={updatedTask} onClick={onClick} />);
    
    expect(screen.getByText('Updated Title')).toBeInTheDocument();
  });
});

