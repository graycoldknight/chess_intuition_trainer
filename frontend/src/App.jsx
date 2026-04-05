import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import ProfileSelect from './components/ProfileSelect';
import Dashboard from './components/Dashboard';
import TrainingSession from './components/TrainingSession';
import ResultsScreen from './components/ResultsScreen';

function App() {
  return (
    <div style={{ fontFamily: 'sans-serif', background: '#1a1a1a', minHeight: '100vh', color: '#fff' }}>
      <Routes>
        <Route path="/" element={<ProfileSelect />} />
        <Route path="/dashboard/:profileId" element={<Dashboard />} />
        <Route path="/train/:profileId" element={<TrainingSession />} />
        <Route path="/results/:profileId" element={<ResultsScreen />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

export default App;
