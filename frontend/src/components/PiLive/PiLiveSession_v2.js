// src/components/PiLive/PiLiveSession.js
// CLEANED VERSION - Uses SimplifiedPiLiveSession component

import React from 'react';
import SimplifiedPiLiveSession from './SimplifiedPiLiveSession';
import './PiLive.css';

const PiLiveSession = ({ onSessionComplete }) => {
  return (
    <SimplifiedPiLiveSession onSessionComplete={onSessionComplete} />
  );
};

export default PiLiveSession;