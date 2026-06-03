import React from 'react';

const DebateLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="flex h-screen">
      <div className="w-72 md:w-72 lg:w-72 side-nav bg-gray-800 p-4">
        {/* Side navigation content */}
      </div>
      <div className="flex-1 pl-72 md:pl-72 lg:pl-72 main-content">
        {children}
      </div>
    </div>
  );
};

export default DebateLayout;