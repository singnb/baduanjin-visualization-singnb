// src/__tests__/auth/AuthContext.test.js

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import axios from 'axios';
import { AuthProvider, useAuth } from '../../auth/AuthContext';

// Test component to access auth context
const TestComponent = () => {
  const { user, loading, isAuthenticated, login, logout } = useAuth();
  
  return (
    <div>
      <div data-testid="loading">{loading.toString()}</div>
      <div data-testid="authenticated">{isAuthenticated().toString()}</div>
      <div data-testid="user">{user ? user.email : 'null'}</div>
      <button 
        data-testid="login-btn" 
        onClick={() => login('test@test.com', 'password')}
      >
        Login
      </button>
      <button data-testid="logout-btn" onClick={logout}>
        Logout
      </button>
    </div>
  );
};

const renderWithRouter = (component) => {
  return render(
    <MemoryRouter>
      <AuthProvider>
        {component}
      </AuthProvider>
    </MemoryRouter>
  );
};

describe('AuthContext', () => {
  let user;

  beforeEach(() => {
    user = userEvent.setup();
    jest.clearAllMocks();
    localStorage.clear();
    delete axios.defaults.headers.common['Authorization'];
  });

  test('initial loading state', async () => {
    renderWithRouter(<TestComponent />);
    
    // Wait for the component to render and check final state
    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false');
    });
    
    // Should not be authenticated initially
    expect(screen.getByTestId('authenticated')).toHaveTextContent('false');
    expect(screen.getByTestId('user')).toHaveTextContent('null');
  });

  test('successful login flow', async () => {
    const mockUser = { 
      id: 1, 
      email: 'test@test.com', 
      role: 'learner', 
      agreement_required: false 
    };
    
    axios.post.mockResolvedValueOnce({
      data: {
        access_token: 'test-token',
        user: mockUser
      }
    });

    renderWithRouter(<TestComponent />);
    
    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false');
    });

    await user.click(screen.getByTestId('login-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true');
    });
    
    // Check that axios.post was called with correct login data
    expect(axios.post).toHaveBeenCalledWith(
      expect.stringContaining('/api/auth/login'),
      {
        email: 'test@test.com',
        password: 'password'
      }
    );
  });

  test('logout functionality', async () => {
    renderWithRouter(<TestComponent />);
    
    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false');
    });

    await user.click(screen.getByTestId('logout-btn'));

    expect(screen.getByTestId('authenticated')).toHaveTextContent('false');
    expect(screen.getByTestId('user')).toHaveTextContent('null');
  });

  test('handles login error', async () => {
    axios.post.mockRejectedValueOnce(new Error('Login failed'));

    renderWithRouter(<TestComponent />);
    
    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false');
    });

    await user.click(screen.getByTestId('login-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('false');
    });
  });
});