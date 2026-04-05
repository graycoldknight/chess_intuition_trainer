import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import ProfileSelect from './components/ProfileSelect';
import TrainingSession from './components/TrainingSession';

function App() {
  return (
    <div style={{ fontFamily: 'sans-serif', background: '#1a1a1a', minHeight: '100vh', color: '#fff' }}>
      <Routes>
        <Route path="/" element={<ProfileSelect />} />
        <Route path="/train/:profileId" element={<TrainingSession />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

export default App;
