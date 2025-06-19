// src/App.js
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './auth/AuthContext';
import ProtectedRoute from './auth/ProtectedRoute';
import LoginForm from './auth/LoginForm';
import RegisterForm from './auth/RegisterForm';
import UserAgreement from './auth/UserAgreement';
import Header from './components/Layout/Header'; 
import VideoManagement from './components/Layout/VideoManagement';
import VideoAnalysis from './components/Analysis/VideoAnalysis';
import ComparisonSelection from './components/Analysis/ComparisonSelection';
import ComparisonView from './components/Analysis/ComparisonView';
import Masters from './components/Layout/Masters';
import Learners from './components/Layout/Learners';
import VideoView from './components/Layout/VideoView';
import './App.css';

// Loading component to show during authentication check
function LoadingScreen() {
  return (
    <div className="loading-container">
      <h2>Loading Baduanjin Analysis...</h2>
      <div className="loading-spinner"></div>
    </div>
  );
}

// Application routes wrapper that handles auth loading state
function AppRoutes() {
  const { loading, user } = useAuth(); // Keep user for the header
  const [comparisonMode, setComparisonMode] = React.useState('sideBySide');
  
  // Show loading screen while authentication is being checked
  if (loading) {
    return <LoadingScreen />;
  }
  
  return (
    <div className="app-container">
      {user && (
        <Header 
          title="Baduanjin Analysis" 
          comparisonMode={comparisonMode}
          setComparisonMode={setComparisonMode}
        />
      )}
      
      <div className="content-area">
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginForm />} />
          <Route path="/register" element={<RegisterForm />} />
          <Route path="/agreement" element={<UserAgreement />} />
          
          {/* Video management */}
          <Route path="/videos" element={
            <ProtectedRoute>
              <VideoManagement />
            </ProtectedRoute>
          } />
          
          {/* Analysis view route */}
          <Route path="/analysis/:videoId" element={
            <ProtectedRoute>
              <VideoAnalysis />
            </ProtectedRoute>
          } />
                   
          {/* Masters page - for learners to find and follow masters */}
          <Route path="/masters" element={
            <ProtectedRoute>
              <Masters />
            </ProtectedRoute>
          } />
          
          {/* Learners page - for masters to manage their learners */}
          <Route path="/learners" element={
            <ProtectedRoute>
              <Learners />
            </ProtectedRoute>
          } />

          <Route path="/video/:videoId" element={
            <ProtectedRoute>
              <Header />
              <VideoView />
            </ProtectedRoute>
          } />
                    
          {/* Comparison Selection route */}
          <Route path="/comparison-selection" element={
            <ProtectedRoute>
              <ComparisonSelection />
            </ProtectedRoute>
          } />
          
          {/* Comparison View route */}
          <Route path="/comparison/:userVideoId/:masterVideoId" element={
            <ProtectedRoute>
              <ComparisonView />
            </ProtectedRoute>
          } />
          
          {/* Redirect root to videos */}
          <Route path="/" element={<Navigate to="/videos" />} />
        </Routes>
      </div>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;