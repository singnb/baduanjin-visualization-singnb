// src/__tests__/auth/RegisterForm.test.js

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import RegisterForm from '../../auth/RegisterForm';

// Mock the AuthContext locally
const mockRegister = jest.fn();
jest.mock('../../auth/AuthContext', () => ({
  useAuth: () => ({
    register: mockRegister
  })
}));

// Mock Link component
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn(),
  Link: ({ children, to }) => <a href={to}>{children}</a>
}));

const renderRegisterForm = () => {
  return render(
    <BrowserRouter>
      <RegisterForm />
    </BrowserRouter>
  );
};

describe('RegisterForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders registration form', () => {
    renderRegisterForm();
    
    expect(screen.getByText(/register for baduanjin analysis/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/role/i)).toBeInTheDocument();
  });

  test('validates password confirmation', async () => {
    const user = userEvent.setup();
    
    renderRegisterForm();
    
    await user.type(screen.getByLabelText(/^password$/i), 'password123');
    await user.type(screen.getByLabelText(/confirm password/i), 'different');
    await user.click(screen.getByRole('button', { name: /register/i }));
    
    expect(screen.getByText('Passwords do not match')).toBeInTheDocument();
  });

  test('validates password length', async () => {
    const user = userEvent.setup();
    
    renderRegisterForm();
    
    await user.type(screen.getByLabelText(/^password$/i), 'short');
    await user.type(screen.getByLabelText(/confirm password/i), 'short');
    await user.click(screen.getByRole('button', { name: /register/i }));
    
    expect(screen.getByText('Password must be at least 8 characters long')).toBeInTheDocument();
  });

  test('successful registration', async () => {
    const user = userEvent.setup();
    mockRegister.mockResolvedValueOnce({ success: true });
    
    renderRegisterForm();
    
    await user.type(screen.getByLabelText(/username/i), 'testuser');
    await user.type(screen.getByLabelText(/email/i), 'test@test.com');
    await user.type(screen.getByLabelText(/^password$/i), 'password123');
    await user.type(screen.getByLabelText(/confirm password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /register/i }));
    
    expect(mockRegister).toHaveBeenCalledWith(
      'testuser',
      'test@test.com', 
      'password123',
      'learner',
      'testuser'
    );
  });
});