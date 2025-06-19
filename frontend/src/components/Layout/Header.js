// src/components/Layout/Header.js

import { useNavigate, NavLink } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import './Header.css';

function Header({ title }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  
  const handleLogout = () => {
    logout();
    navigate('/login');
  };
   
  return (
    <header className="header">
      <div className="header-left">
        <div className="header-title">
          <h1>{title || "Baduanjin Analysis"}</h1>
        </div>
        
        {user && (
          <nav className="header-nav">
            <ul>
              <li>
                <NavLink to="/videos" className={({ isActive }) => isActive ? "active" : ""}>
                  Videos
                </NavLink>
              </li>
              
              {/* Show Comparison only for learners, not masters */}
              {user.role !== 'master' && (
                <li>
                  <NavLink to="/comparison-selection" className={({ isActive }) => isActive ? "active" : ""}>
                    Comparison
                  </NavLink>
                </li>
              )}
              
              {/* Show appropriate navigation based on role */}
              {user.role === 'master' ? (
                <>
                  <li>
                    <NavLink to="/learners" className={({ isActive }) => isActive ? "active" : ""}>
                      Learners
                    </NavLink>
                  </li>
                  {/* Optional: Add more master-specific links here */}
                </>
              ) : (
                <>
                  <li>
                    <NavLink to="/masters" className={({ isActive }) => isActive ? "active" : ""}>
                      Masters
                    </NavLink>
                  </li>
                  {/* Optional: Add more learner-specific links here */}
                </>
              )}
            </ul>
          </nav>
        )}
      </div>
      
      <div className="header-right">
        <div className="user-controls">
          {user ? (
            <>
              <div className="user-info">
                <span className="welcome-text">Welcome, {user.name}</span>
                <span className="user-role">
                  {user.role === 'master' ? 'Master' : 'Learner'}
                </span>
              </div>
              <button className="logout-button" onClick={handleLogout}>
                Logout
              </button>
            </>
          ) : (
            <button className="login-button" onClick={() => navigate('/login')}>
              Login
            </button>
          )}
        </div>
      </div>
    </header>
  );
}

export default Header;