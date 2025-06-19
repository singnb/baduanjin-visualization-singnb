// src/components/Layout/VideoUpload.js
import React, { useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../auth/AuthContext';
import './Layout.css'; 

const BACKEND_URL = 'https://baduanjin-backend-docker.azurewebsites.net';

const VideoUpload = ({ onUploadComplete }) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [brocadeType, setBrocadeType] = useState('FIRST'); // Default type
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const { token } = useAuth();
  
  const handleFileChange = (e) => {
    if (e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a video file');
      return;
    }
    
    setUploading(true);
    setError(null);
    
    const formData = new FormData();
    formData.append('title', title);
    formData.append('description', description || '');
    formData.append('brocade_type', brocadeType);
    formData.append('file', file);
    
    try {
      const response = await axios.post(`${BACKEND_URL}/api/videos/upload`, formData, {
        headers: {
          // 'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${token}`
        }
      });
      
      setUploading(false);
      if (onUploadComplete) {
        onUploadComplete(response.data);
      }
      
      // Reset form
      setTitle('');
      setDescription('');
      setBrocadeType('FIRST');
      setFile(null);
      
    } catch (error) {
      setUploading(false);
      setError(error.response?.data?.detail || 'Error uploading video');
      console.error('Upload error:', error);
    }
  };
  
  return (
    <div className="video-upload-container">
      <div className="section-header">
        <h2>Upload Exercise Video</h2>
      </div>
      
      {error && <div className="error-message">{error}</div>}
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="title">Title</label>
          <input
            id="title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
        </div>
        
        <div className="form-group">
          <label htmlFor="description">Description (Optional)</label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        
        <div className="form-group">
          <label htmlFor="brocadeType">Brocade Type</label>
          <select
            id="brocadeType"
            value={brocadeType}
            onChange={(e) => setBrocadeType(e.target.value)}
            required
          >
            <option value="FIRST">First Brocade</option>
            <option value="SECOND">Second Brocade</option>
            <option value="THIRD">Third Brocade</option>
            <option value="FOURTH">Fourth Brocade</option>
            <option value="FIFTH">Fifth Brocade</option>
            <option value="SIXTH">Sixth Brocade</option>
            <option value="SEVENTH">Seventh Brocade</option>
            <option value="EIGHTH">Eighth Brocade</option>
          </select>
        </div>
        
        <div className="form-group">
          <label htmlFor="videoFile">Video File</label>
          <input
            id="videoFile"
            type="file"
            accept="video/*"
            onChange={handleFileChange}
            required
          />
        </div>
        
        <button 
          type="submit" 
          disabled={uploading}
          className="upload-btn"
        >
          {uploading ? 'Uploading...' : 'Upload Video'}
        </button>
      </form>
    </div>
  );
};

export default VideoUpload;
