import { BrowserRouter, Routes, Route, Navigate, useParams } from 'react-router-dom';
import Home from './pages/Home';
import Game from './pages/Game';
import Review from './pages/Review';

const RoomRedirect = () => {
  const { password } = useParams<{ password: string }>();
  return <Navigate to={`/game/${password}`} replace />;
};

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/room/:password" element={<RoomRedirect />} />
        <Route path="/game/:password" element={<Game />} />
        <Route path="/review/:password" element={<Review />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
