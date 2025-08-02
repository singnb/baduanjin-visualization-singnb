// src/__tests__/auth/LoginForm.test.js
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import LoginForm from '../../auth/LoginForm';

// Mock the AuthContext locally
const mockLogin = jest.fn();
jest.mock('../../auth/AuthContext', () => ({
  useAuth: () => ({
    login: mockLogin
  })
}));

// Mock useNavigate locally
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate
}));

const renderLoginForm = () => {
  return render(
    <BrowserRouter>
      <LoginForm />
    </BrowserRouter>
  );
};

describe('LoginForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders login form', () => {
    renderLoginForm();
    
    expect(screen.getByText(/sign in to baduanjin analyzer/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  test('handles successful login', async () => {
    const user = userEvent.setup();
    mockLogin.mockResolvedValueOnce({ success: true });
    
    renderLoginForm();
    
    await user.type(screen.getByLabelText(/email/i), 'test@test.com');
    await user.type(screen.getByLabelText(/password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /sign in/i }));
    
    expect(mockLogin).toHaveBeenCalledWith('test@test.com', 'password123');
  });

  test('displays error message on login failure', async () => {
    const user = userEvent.setup();
    mockLogin.mockResolvedValueOnce({ 
      success: false, 
      message: 'Invalid credentials' 
    });
    
    renderLoginForm();
    
    await user.type(screen.getByLabelText(/email/i), 'test@test.com');
    await user.type(screen.getByLabelText(/password/i), 'wrongpassword');
    await user.click(screen.getByRole('button', { name: /sign in/i }));
    
    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
    });
  });
});