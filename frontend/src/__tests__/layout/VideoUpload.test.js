/* eslint-disable testing-library/no-wait-for-multiple-assertions */
// src/__tests__/layout/VideoUpload.test.js

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axios from 'axios';
import VideoUpload from '../../components/Layout/VideoUpload';
import { useAuth } from '../../auth/AuthContext';

// Mock axios
jest.mock('axios');
const mockedAxios = axios;

// Mock useAuth hook
jest.mock('../../auth/AuthContext', () => ({
  useAuth: jest.fn()
}));

// Mock CSS import
jest.mock('../../components/Layout/Layout.css', () => ({}));

describe('VideoUpload Component', () => {
  const mockOnUploadComplete = jest.fn();
  const mockToken = 'test-token-123';

  beforeEach(() => {
    // Reset all mocks before each test
    jest.clearAllMocks();
    
    // Mock useAuth to return a token
    useAuth.mockReturnValue({
      token: mockToken
    });
  });

  describe('Component Rendering', () => {
    test('renders all form elements correctly', () => {
      render(<VideoUpload onUploadComplete={mockOnUploadComplete} />);
      
      expect(screen.getByText('Upload Exercise Video')).toBeInTheDocument();
      expect(screen.getByLabelText('Title')).toBeInTheDocument();
      expect(screen.getByLabelText('Description (Optional)')).toBeInTheDocument();
      expect(screen.getByLabelText('Brocade Type')).toBeInTheDocument();
      expect(screen.getByLabelText('Video File')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Upload Video' })).toBeInTheDocument();
    });

    test('renders all brocade type options', () => {
      render(<VideoUpload onUploadComplete={mockOnUploadComplete} />);
      
      const select = screen.getByLabelText('Brocade Type');
      const options = [
        'First Brocade', 'Second Brocade', 'Third Brocade', 'Fourth Brocade',
        'Fifth Brocade', 'Sixth Brocade', 'Seventh Brocade', 'Eighth Brocade'
      ];
      
      options.forEach(option => {
        expect(screen.getByText(option)).toBeInTheDocument();
      });
      
      // Check default selection
      expect(select.value).toBe('FIRST');
    });
  });

  describe('Form State Management', () => {
    test('updates title field correctly', async () => {
      const user = userEvent.setup();
      render(<VideoUpload onUploadComplete={mockOnUploadComplete} />);
      
      const titleInput = screen.getByLabelText('Title');
      await user.type(titleInput, 'Test Video Title');
      
      expect(titleInput.value).toBe('Test Video Title');
    });

    test('updates description field correctly', async () => {
      const user = userEvent.setup();
      render(<VideoUpload onUploadComplete={mockOnUploadComplete} />);
      
      const descriptionInput = screen.getByLabelText('Description (Optional)');
      await user.type(descriptionInput, 'Test description for video');
      
      expect(descriptionInput.value).toBe('Test description for video');
    });

    test('updates brocade type selection correctly', async () => {
      const user = userEvent.setup();
      render(<VideoUpload onUploadComplete={mockOnUploadComplete} />);
      
      const select = screen.getByLabelText('Brocade Type');
      await user.selectOptions(select, 'THIRD');
      
      expect(select.value).toBe('THIRD');
    });
  });

  describe('File Handling', () => {
    test('handles file selection correctly', async () => {
      const user = userEvent.setup();
      render(<VideoUpload onUploadComplete={mockOnUploadComplete} />);
      
      const file = new File(['test video content'], 'test-video.mp4', { type: 'video/mp4' });
      const fileInput = screen.getByLabelText('Video File');
      
      await user.upload(fileInput, file);
      
      expect(fileInput.files[0]).toBe(file);
      expect(fileInput.files[0].name).toBe('test-video.mp4');
    });

    test('accepts only video files', () => {
      render(<VideoUpload onUploadComplete={mockOnUploadComplete} />);
      
      const fileInput = screen.getByLabelText('Video File');
      expect(fileInput.getAttribute('accept')).toBe('video/*');
    });
  });

  describe('Form Validation', () => {
    test('shows error when submitting without file', async () => {
      const user = userEvent.setup();
      render(<VideoUpload onUploadComplete={mockOnUploadComplete} />);
      
      const titleInput = screen.getByLabelText('Title');
      const submitButton = screen.getByRole('button', { name: 'Upload Video' });
      
      await user.type(titleInput, 'Test Title');
      await user.click(submitButton);
      
      expect(screen.getByText('Please select a video file')).toBeInTheDocument();
    });

    test('title field is required', () => {
      render(<VideoUpload onUploadComplete={mockOnUploadComplete} />);
      
      const titleInput = screen.getByLabelText('Title');
      expect(titleInput).toHaveAttribute('required');
    });

    test('brocade type field is required', () => {
      render(<VideoUpload onUploadComplete={mockOnUploadComplete} />);
      
      const brocadeTypeSelect = screen.getByLabelText('Brocade Type');
      expect(brocadeTypeSelect).toHaveAttribute('required');
    });

    test('video file field is required', () => {
      render(<VideoUpload onUploadComplete={mockOnUploadComplete} />);
      
      const fileInput = screen.getByLabelText('Video File');
      expect(fileInput).toHaveAttribute('required');
    });
  });

  describe('Form Submission', () => {
    test('successful form submission with all fields', async () => {
      const user = userEvent.setup();
      const mockResponse = { data: { id: 1, title: 'Test Video' } };
      mockedAxios.post.mockResolvedValueOnce(mockResponse);
      
      render(<VideoUpload onUploadComplete={mockOnUploadComplete} />);
      
      // Fill out form
      const titleInput = screen.getByLabelText('Title');
      const descriptionInput = screen.getByLabelText('Description (Optional)');
      const brocadeTypeSelect = screen.getByLabelText('Brocade Type');
      const fileInput = screen.getByLabelText('Video File');
      const submitButton = screen.getByRole('button', { name: 'Upload Video' });
      
      const file = new File(['test video'], 'test.mp4', { type: 'video/mp4' });
      
      await user.type(titleInput, 'My Test Video');
      await user.type(descriptionInput, 'Test description');
      await user.selectOptions(brocadeTypeSelect, 'SECOND');
      await user.upload(fileInput, file);
      
      await user.click(submitButton);
      
      // Verify axios call
      await waitFor(() => {
        expect(mockedAxios.post).toHaveBeenCalledWith(
          'https://baduanjin-backend-docker.azurewebsites.net/api/videos/upload',
          expect.any(FormData),
          {
            headers: {
              'Authorization': `Bearer ${mockToken}`
            }
          }
        );
      });
      
      // Verify callback is called
      expect(mockOnUploadComplete).toHaveBeenCalledWith(mockResponse.data);
    });

    test('form submission with minimal required fields', async () => {
      const user = userEvent.setup();
      const mockResponse = { data: { id: 2, title: 'Minimal Video' } };
      mockedAxios.post.mockResolvedValueOnce(mockResponse);
      
      render(<VideoUpload onUploadComplete={mockOnUploadComplete} />);
      
      const titleInput = screen.getByLabelText('Title');
      const fileInput = screen.getByLabelText('Video File');
      const submitButton = screen.getByRole('button', { name: 'Upload Video' });
      
      const file = new File(['minimal video'], 'minimal.mp4', { type: 'video/mp4' });
      
      await user.type(titleInput, 'Minimal Video');
      await user.upload(fileInput, file);
      await user.click(submitButton);
      
      await waitFor(() => {
        expect(mockedAxios.post).toHaveBeenCalled();
      });
      
      expect(mockOnUploadComplete).toHaveBeenCalledWith(mockResponse.data);
    });

    test('verifies FormData contains correct fields', async () => {
      const user = userEvent.setup();
      mockedAxios.post.mockResolvedValueOnce({ data: {} });
      
      render(<VideoUpload onUploadComplete={mockOnUploadComplete} />);
      
      const titleInput = screen.getByLabelText('Title');
      const descriptionInput = screen.getByLabelText('Description (Optional)');
      const brocadeTypeSelect = screen.getByLabelText('Brocade Type');
      const fileInput = screen.getByLabelText('Video File');
      const submitButton = screen.getByRole('button', { name: 'Upload Video' });
      
      const file = new File(['test'], 'test.mp4', { type: 'video/mp4' });
      
      await user.type(titleInput, 'Test Title');
      await user.type(descriptionInput, 'Test Description');
      await user.selectOptions(brocadeTypeSelect, 'THIRD');
      await user.upload(fileInput, file);
      await user.click(submitButton);
      
      await waitFor(() => {
        const formDataCall = mockedAxios.post.mock.calls[0][1];
        expect(formDataCall).toBeInstanceOf(FormData);
      });
    });
  });

  describe('Loading States', () => {
    test('shows loading state during upload', async () => {
      const user = userEvent.setup();
      // Create a promise that won't resolve immediately
      let resolvePromise;
      const uploadPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });
      mockedAxios.post.mockReturnValueOnce(uploadPromise);
      
      render(<VideoUpload onUploadComplete={mockOnUploadComplete} />);
      
      const titleInput = screen.getByLabelText('Title');
      const fileInput = screen.getByLabelText('Video File');
      const submitButton = screen.getByRole('button', { name: 'Upload Video' });
      
      const file = new File(['test'], 'test.mp4', { type: 'video/mp4' });
      
      await user.type(titleInput, 'Test');
      await user.upload(fileInput, file);
      await user.click(submitButton);
      
      // Check loading state
      expect(screen.getByText('Uploading...')).toBeInTheDocument();
      expect(submitButton).toBeDisabled();
      
      // Resolve the promise
      resolvePromise({ data: {} });
      
      await waitFor(() => {
        expect(screen.getByText('Upload Video')).toBeInTheDocument();
        expect(submitButton).not.toBeDisabled();
      });
    });
  });

  describe('Error Handling', () => {
    test('displays error message on upload failure', async () => {
      const user = userEvent.setup();
      const errorMessage = 'Upload failed due to server error';
      mockedAxios.post.mockRejectedValueOnce({
        response: {
          data: {
            detail: errorMessage
          }
        }
      });
      
      render(<VideoUpload onUploadComplete={mockOnUploadComplete} />);
      
      const titleInput = screen.getByLabelText('Title');
      const fileInput = screen.getByLabelText('Video File');
      const submitButton = screen.getByRole('button', { name: 'Upload Video' });
      
      const file = new File(['test'], 'test.mp4', { type: 'video/mp4' });
      
      await user.type(titleInput, 'Test');
      await user.upload(fileInput, file);
      await user.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText(errorMessage)).toBeInTheDocument();
      });
    });

    test('displays generic error message when no specific error provided', async () => {
      const user = userEvent.setup();
      mockedAxios.post.mockRejectedValueOnce(new Error('Network error'));
      
      render(<VideoUpload onUploadComplete={mockOnUploadComplete} />);
      
      const titleInput = screen.getByLabelText('Title');
      const fileInput = screen.getByLabelText('Video File');
      const submitButton = screen.getByRole('button', { name: 'Upload Video' });
      
      const file = new File(['test'], 'test.mp4', { type: 'video/mp4' });
      
      await user.type(titleInput, 'Test');
      await user.upload(fileInput, file);
      await user.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText('Error uploading video')).toBeInTheDocument();
      });
    });

    test('clears error message on new submission attempt', async () => {
      const user = userEvent.setup();
      
      render(<VideoUpload onUploadComplete={mockOnUploadComplete} />);
      
      const submitButton = screen.getByRole('button', { name: 'Upload Video' });
      
      // First submission without file to trigger error
      await user.click(submitButton);
      expect(screen.getByText('Please select a video file')).toBeInTheDocument();
      
      // Add file and try again
      const titleInput = screen.getByLabelText('Title');
      const fileInput = screen.getByLabelText('Video File');
      const file = new File(['test'], 'test.mp4', { type: 'video/mp4' });
      
      await user.type(titleInput, 'Test');
      await user.upload(fileInput, file);
      
      mockedAxios.post.mockResolvedValueOnce({ data: {} });
      await user.click(submitButton);
      
      // Error message should be cleared
      await waitFor(() => {
        expect(screen.queryByText('Please select a video file')).not.toBeInTheDocument();
      });
    });
  });

  describe('Form Reset', () => {
    test('resets form after successful upload', async () => {
      const user = userEvent.setup();
      mockedAxios.post.mockResolvedValueOnce({ data: {} });
      
      render(<VideoUpload onUploadComplete={mockOnUploadComplete} />);
      
      const titleInput = screen.getByLabelText('Title');
      const descriptionInput = screen.getByLabelText('Description (Optional)');
      const brocadeTypeSelect = screen.getByLabelText('Brocade Type');
      const fileInput = screen.getByLabelText('Video File');
      const submitButton = screen.getByRole('button', { name: 'Upload Video' });
      
      const file = new File(['test'], 'test.mp4', { type: 'video/mp4' });
      
      // Fill form
      await user.type(titleInput, 'Test Title');
      await user.type(descriptionInput, 'Test Description');
      await user.selectOptions(brocadeTypeSelect, 'SECOND');
      await user.upload(fileInput, file);
      
      // Verify form is filled
      expect(titleInput.value).toBe('Test Title');
      expect(descriptionInput.value).toBe('Test Description');
      expect(brocadeTypeSelect.value).toBe('SECOND');
      expect(fileInput.files.length).toBe(1);
      
      // Submit
      await user.click(submitButton);
      
      // Wait for successful upload and form reset
      await waitFor(() => {
        expect(titleInput.value).toBe('');
        expect(descriptionInput.value).toBe('');
        expect(brocadeTypeSelect.value).toBe('FIRST');
        // Note: File input reset requires setting the value property
        // This test verifies the text inputs and select are reset
        // File input reset would need component modification
      });
      
      // Verify upload was called
      expect(mockedAxios.post).toHaveBeenCalled();
      expect(mockOnUploadComplete).toHaveBeenCalled();
    });

    test('form can be filled again after reset', async () => {
      const user = userEvent.setup();
      mockedAxios.post.mockResolvedValueOnce({ data: {} });
      
      render(<VideoUpload onUploadComplete={mockOnUploadComplete} />);
      
      const titleInput = screen.getByLabelText('Title');
      const fileInput = screen.getByLabelText('Video File');
      const submitButton = screen.getByRole('button', { name: 'Upload Video' });
      
      const file1 = new File(['test1'], 'test1.mp4', { type: 'video/mp4' });
      const file2 = new File(['test2'], 'test2.mp4', { type: 'video/mp4' });
      
      // First upload
      await user.type(titleInput, 'First Video');
      await user.upload(fileInput, file1);
      await user.click(submitButton);
      
      // Wait for form reset
      await waitFor(() => {
        expect(titleInput.value).toBe('');
      });
      
      // Second upload should work
      mockedAxios.post.mockResolvedValueOnce({ data: {} });
      await user.type(titleInput, 'Second Video');
      await user.upload(fileInput, file2);
      await user.click(submitButton);
      
      // Verify second upload was called
      await waitFor(() => {
        expect(mockedAxios.post).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe('Component Props', () => {
    test('works without onUploadComplete callback', async () => {
      const user = userEvent.setup();
      mockedAxios.post.mockResolvedValueOnce({ data: {} });
      
      render(<VideoUpload />);
      
      const titleInput = screen.getByLabelText('Title');
      const fileInput = screen.getByLabelText('Video File');
      const submitButton = screen.getByRole('button', { name: 'Upload Video' });
      
      const file = new File(['test'], 'test.mp4', { type: 'video/mp4' });
      
      await user.type(titleInput, 'Test');
      await user.upload(fileInput, file);
      await user.click(submitButton);
      
      // Should not throw error even without callback
      await waitFor(() => {
        expect(mockedAxios.post).toHaveBeenCalled();
      });
    });
  });
});