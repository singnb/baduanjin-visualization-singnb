/* eslint-disable testing-library/no-container */
/* eslint-disable testing-library/no-node-access */
// src/__tests__/layout/Header.test.js

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Header from '../../components/Layout/Header';
import { useAuth } from '../../auth/AuthContext';

// Mock the useAuth hook
jest.mock('../../auth/AuthContext', () => ({
  useAuth: jest.fn(),
}));

// Mock react-router-dom hooks
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

// Test wrapper component to provide Router context
const TestWrapper = ({ children }) => (
  <BrowserRouter>{children}</BrowserRouter>
);

describe('Header Component', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
  });

  describe('When user is not authenticated', () => {
    beforeEach(() => {
      useAuth.mockReturnValue({
        user: null,
        logout: jest.fn(),
      });
    });

    test('should render default title when no title prop is provided', () => {
      render(
        <TestWrapper>
          <Header />
        </TestWrapper>
      );
      
      expect(screen.getByText('Baduanjin Analysis')).toBeInTheDocument();
    });

    test('should render custom title when title prop is provided', () => {
      render(
        <TestWrapper>
          <Header title="Custom Title" />
        </TestWrapper>
      );
      
      expect(screen.getByText('Custom Title')).toBeInTheDocument();
    });

    test('should show login button when user is not authenticated', () => {
      render(
        <TestWrapper>
          <Header />
        </TestWrapper>
      );
      
      expect(screen.getByText('Login')).toBeInTheDocument();
    });

    test('should not show navigation menu when user is not authenticated', () => {
      render(
        <TestWrapper>
          <Header />
        </TestWrapper>
      );
      
      expect(screen.queryByText('Live Sessions')).not.toBeInTheDocument();
      expect(screen.queryByText('Videos')).not.toBeInTheDocument();
      expect(screen.queryByText('Comparison')).not.toBeInTheDocument();
    });

    test('should navigate to login when login button is clicked', () => {
      render(
        <TestWrapper>
          <Header />
        </TestWrapper>
      );
      
      const loginButton = screen.getByText('Login');
      fireEvent.click(loginButton);
      
      expect(mockNavigate).toHaveBeenCalledWith('/login');
    });
  });

  describe('When user is authenticated as learner', () => {
    const mockLearnerUser = {
      name: 'John Doe',
      role: 'learner',
    };

    const mockLogout = jest.fn();

    beforeEach(() => {
      useAuth.mockReturnValue({
        user: mockLearnerUser,
        logout: mockLogout,
      });
    });

    test('should display user welcome message and role', () => {
      render(
        <TestWrapper>
          <Header />
        </TestWrapper>
      );
      
      expect(screen.getByText('Welcome, John Doe')).toBeInTheDocument();
      expect(screen.getByText('Learner')).toBeInTheDocument();
    });

    test('should show logout button', () => {
      render(
        <TestWrapper>
          <Header />
        </TestWrapper>
      );
      
      expect(screen.getByText('Logout')).toBeInTheDocument();
    });

    test('should show appropriate navigation links for learner', () => {
      render(
        <TestWrapper>
          <Header />
        </TestWrapper>
      );
      
      expect(screen.getByText('Live Sessions')).toBeInTheDocument();
      expect(screen.getByText('Videos')).toBeInTheDocument();
      expect(screen.getByText('Comparison')).toBeInTheDocument();
      expect(screen.getByText('Masters')).toBeInTheDocument();
    });

    test('should not show learners link for learner users', () => {
      render(
        <TestWrapper>
          <Header />
        </TestWrapper>
      );
      
      expect(screen.queryByText('Learners')).not.toBeInTheDocument();
    });

    test('should call logout and navigate to login when logout button is clicked', () => {
      render(
        <TestWrapper>
          <Header />
        </TestWrapper>
      );
      
      const logoutButton = screen.getByText('Logout');
      fireEvent.click(logoutButton);
      
      expect(mockLogout).toHaveBeenCalledTimes(1);
      expect(mockNavigate).toHaveBeenCalledWith('/login');
    });
  });

  describe('When user is authenticated as master', () => {
    const mockMasterUser = {
      name: 'Master Smith',
      role: 'master',
    };

    const mockLogout = jest.fn();

    beforeEach(() => {
      useAuth.mockReturnValue({
        user: mockMasterUser,
        logout: mockLogout,
      });
    });

    test('should display master user welcome message and role', () => {
      render(
        <TestWrapper>
          <Header />
        </TestWrapper>
      );
      
      expect(screen.getByText('Welcome, Master Smith')).toBeInTheDocument();
      expect(screen.getByText('Master')).toBeInTheDocument();
    });

    test('should show appropriate navigation links for master', () => {
      render(
        <TestWrapper>
          <Header />
        </TestWrapper>
      );
      
      expect(screen.getByText('Live Sessions')).toBeInTheDocument();
      expect(screen.getByText('Videos')).toBeInTheDocument();
      expect(screen.getByText('Learners')).toBeInTheDocument();
    });

    test('should not show comparison link for master users', () => {
      render(
        <TestWrapper>
          <Header />
        </TestWrapper>
      );
      
      expect(screen.queryByText('Comparison')).not.toBeInTheDocument();
    });

    test('should not show masters link for master users', () => {
      render(
        <TestWrapper>
          <Header />
        </TestWrapper>
      );
      
      expect(screen.queryByText('Masters')).not.toBeInTheDocument();
    });

    test('should call logout and navigate to login when logout button is clicked', () => {
      render(
        <TestWrapper>
          <Header />
        </TestWrapper>
      );
      
      const logoutButton = screen.getByText('Logout');
      fireEvent.click(logoutButton);
      
      expect(mockLogout).toHaveBeenCalledTimes(1);
      expect(mockNavigate).toHaveBeenCalledWith('/login');
    });
  });

  describe('Navigation links behavior', () => {
    const mockLearnerUser = {
      name: 'Test User',
      role: 'learner',
    };

    beforeEach(() => {
      useAuth.mockReturnValue({
        user: mockLearnerUser,
        logout: jest.fn(),
      });
    });

    test('should render navigation links with correct href attributes', () => {
      render(
        <TestWrapper>
          <Header />
        </TestWrapper>
      );
      
      const liveSessionsLink = screen.getByText('Live Sessions').closest('a');
      const videosLink = screen.getByText('Videos').closest('a');
      const comparisonLink = screen.getByText('Comparison').closest('a');
      const mastersLink = screen.getByText('Masters').closest('a');
      
      expect(liveSessionsLink).toHaveAttribute('href', '/live-sessions');
      expect(videosLink).toHaveAttribute('href', '/videos');
      expect(comparisonLink).toHaveAttribute('href', '/comparison-selection');
      expect(mastersLink).toHaveAttribute('href', '/masters');
    });
  });

  describe('Component structure and CSS classes', () => {
    beforeEach(() => {
      useAuth.mockReturnValue({
        user: null,
        logout: jest.fn(),
      });
    });

    test('should render with correct CSS classes and structure', () => {
      const { container } = render(
        <TestWrapper>
          <Header />
        </TestWrapper>
      );
      
      expect(container.querySelector('.header')).toBeInTheDocument();
      expect(container.querySelector('.header-left')).toBeInTheDocument();
      expect(container.querySelector('.header-right')).toBeInTheDocument();
      expect(container.querySelector('.header-title')).toBeInTheDocument();
      expect(container.querySelector('.user-controls')).toBeInTheDocument();
    });

    test('should show login button with correct CSS class when not authenticated', () => {
      render(
        <TestWrapper>
          <Header />
        </TestWrapper>
      );
      
      const loginButton = screen.getByText('Login');
      expect(loginButton).toHaveClass('login-button');
    });

    test('should show logout button with correct CSS class when authenticated', () => {
      useAuth.mockReturnValue({
        user: { name: 'Test User', role: 'learner' },
        logout: jest.fn(),
      });

      render(
        <TestWrapper>
          <Header />
        </TestWrapper>
      );
      
      const logoutButton = screen.getByText('Logout');
      expect(logoutButton).toHaveClass('logout-button');
    });
  });

  describe('Edge cases and error handling', () => {
    test('should handle undefined user object gracefully', () => {
      useAuth.mockReturnValue({
        user: undefined,
        logout: jest.fn(),
      });

      expect(() => {
        render(
          <TestWrapper>
            <Header />
          </TestWrapper>
        );
      }).not.toThrow();
      
      expect(screen.getByText('Login')).toBeInTheDocument();
    });

    test('should handle user object without name property', () => {
      useAuth.mockReturnValue({
        user: { role: 'learner' },
        logout: jest.fn(),
      });

      render(
        <TestWrapper>
          <Header />
        </TestWrapper>
      );
      
      // Should still render but with undefined name
      expect(screen.getByText('Welcome,')).toBeInTheDocument();
    });

    test('should handle user object without role property', () => {
      useAuth.mockReturnValue({
        user: { name: 'Test User' },
        logout: jest.fn(),
      });

      render(
        <TestWrapper>
          <Header />
        </TestWrapper>
      );
      
      // Should render with Learner as default (since role !== 'master')
      expect(screen.getByText('Learner')).toBeInTheDocument();
    });
  });
});