// src/__tests__/auth/ProtectedRoute.test.js
import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import ProtectedRoute from '../../auth/ProtectedRoute';

// Mock auth context locally
const mockIsAuthenticated = jest.fn();
let mockLoading = false;

jest.mock('../../auth/AuthContext', () => ({
  useAuth: () => ({
    isAuthenticated: mockIsAuthenticated,
    loading: mockLoading
  })
}));

// Mock Navigate component locally
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  Navigate: ({ to }) => <div data-testid="navigate">{to}</div>
}));

const TestChild = () => <div data-testid="protected-content">Protected Content</div>;

const renderProtectedRoute = () => {
  return render(
    <BrowserRouter>
      <ProtectedRoute>
        <TestChild />
      </ProtectedRoute>
    </BrowserRouter>
  );
};

describe('ProtectedRoute', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockLoading = false;
  });

  test('shows loading state when auth is loading', () => {
    mockLoading = true;
    mockIsAuthenticated.mockReturnValue(false);
    
    renderProtectedRoute();
    
    expect(screen.getByText('Verifying authentication...')).toBeInTheDocument();
  });

  test('renders children when authenticated', () => {
    mockLoading = false;
    mockIsAuthenticated.mockReturnValue(true);
    
    renderProtectedRoute();
    
    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
  });

  test('redirects to login when not authenticated', () => {
    mockLoading = false;
    mockIsAuthenticated.mockReturnValue(false);
    
    renderProtectedRoute();
    
    expect(screen.getByTestId('navigate')).toHaveTextContent('/login');
  });
});