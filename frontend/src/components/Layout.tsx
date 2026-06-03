import React from 'react';

const Layout = ({ children }) => {
  return (
    <div className="flex flex-row md:flex-col h-screen">
      {children}
    </div>
  );
};

export default Layout;