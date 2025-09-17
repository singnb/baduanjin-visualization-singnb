// src/__tests__/analysis/ComparisonView.test.js

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { BrowserRouter } from 'react-router-dom';

// Mock navigate function FIRST
const mockNavigate = jest.fn();

// Mock ALL modules before any imports
jest.mock('axios', () => ({
  get: jest.fn(() => Promise.resolve({ data: { recommendations: [] } }))
}));

jest.mock('../../auth/AuthContext', () => ({
  useAuth: () => ({
    token: 'mock-token',
    user: { id: 'user123' }
  })
}));

jest.mock('../../services/dataLoader', () => ({
  loadComparisonData: jest.fn(() => Promise.resolve({
    learnerData: [{ timestamp: 0, value: 10 }],
    masterData: [{ timestamp: 0, value: 12 }]
  }))
}));

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useParams: () => ({
    userVideoId: 'user123',
    masterVideoId: 'master456'
  }),
  useNavigate: () => mockNavigate
}));

// Mock chart components to avoid any complex rendering
jest.mock('../../components/Charts/JointAngleChart', () => {
  return function JointAngleChart() {
    return <div data-testid="joint-angle-chart">Joint Angle Chart</div>;
  };
});

jest.mock('../../components/Charts/SmoothnessChart', () => {
  return function SmoothnessChart() {
    return <div data-testid="smoothness-chart">Smoothness Chart</div>;
  };
});

jest.mock('../../components/Charts/SymmetryChart', () => {
  return function SymmetryChart() {
    return <div data-testid="symmetry-chart">Symmetry Chart</div>;
  };
});

jest.mock('../../components/Charts/BalanceChart', () => {
  return function BalanceChart() {
    return <div data-testid="balance-chart">Balance Chart</div>;
  };
});

// Now import the component AFTER all mocks are set up
import ComparisonView from '../../components/Analysis/ComparisonView';

describe('ComparisonView', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const renderComponent = () => {
    return render(
      <BrowserRouter>
        <ComparisonView />
      </BrowserRouter>
    );
  };

  test('renders loading state initially', () => {
    renderComponent();
    expect(screen.getByText(/Loading comparison data/i)).toBeInTheDocument();
  });

  test('renders main header', async () => {
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('Movement Analysis Comparison')).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  test('displays video IDs', async () => {
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText(/user123.*master456/i)).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  test('shows tab navigation', async () => {
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('Joint Angles')).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  test('displays back button', async () => {
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('Back to Selection')).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  test('handles back navigation', async () => {
    renderComponent();
    
    await waitFor(() => {
      const backButton = screen.getByText('Back to Selection');
      expect(backButton).toBeInTheDocument();
      
      fireEvent.click(backButton);
      expect(mockNavigate).toHaveBeenCalledWith('/comparison-selection');
    }, { timeout: 3000 });
  });
});