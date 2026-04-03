'use client';
import React, { createContext, useState, useEffect } from 'react';
import AxiosInstance from "@/components/AxiosInstance";

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  console.log('AuthProvider is rendered');

  const [token, setToken] = useState(null);
  const [refreshToken, setRefreshToken] = useState(null);
  const [permissions, setPermissions] = useState([]);
  const [role, setRole] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Load data from localStorage on mount
    const storedToken = localStorage.getItem('access_token');
    const storedRefreshToken = localStorage.getItem('refresh_token');
    const storedPermissions = localStorage.getItem('permissions');
    const storedRole = localStorage.getItem('role');
    const storedUser = localStorage.getItem('user');

    console.log('Loading auth data from localStorage...');

    if (storedToken) {
      setToken(storedToken);
      console.log('Loaded access token');
    }

    if (storedRefreshToken) {
      setRefreshToken(storedRefreshToken);
    }

    if (storedPermissions) {
      try {
        const parsedPermissions = JSON.parse(storedPermissions);
        setPermissions(parsedPermissions);
        console.log('Loaded permissions:', parsedPermissions);
      } catch (error) {
        console.error('Error parsing permissions:', error);
        setPermissions([]);
      }
    }

    if (storedRole) {
      try {
        const parsedRole = JSON.parse(storedRole);
        setRole(parsedRole);
        console.log('Loaded role:', parsedRole);
      } catch (error) {
        console.error('Error parsing role:', error);
        setRole(null);
      }
    }

    if (storedUser) {
      try {
        const parsedUser = JSON.parse(storedUser);
        setUser(parsedUser);
        console.log('Loaded user:', parsedUser);
      } catch (error) {
        console.error('Error parsing user:', error);
        setUser(null);
      }
    }

    setLoading(false);
  }, []);

  // const login = (apiResponse) => {
  //   console.log('Login function called with response:', apiResponse);
    
  //   // Backend returns: { message: "Successful", data: {...}, count: null }
  //   // Extract data from the nested data object
  //   const responseData = apiResponse.data;
    
  //   if (!responseData) {
  //     console.error('No data in API response');
  //     return;
  //   }

  //   const accessToken = responseData.access_token;
  //   const refreshTokenValue = responseData.refresh_token;
  //   const userPermissions = responseData.permissions || [];
  //   const userRole = responseData.Role;
  //   const userData = {
  //     id: responseData.id,
  //     name: responseData.name,
  //     username: responseData.username,
  //     email: responseData.email,
  //     mobile: responseData.mobile,
  //     is_superuser: responseData.is_superuser,
  //     profile_image: responseData.profile_image,
  //     role_name: responseData.role_name,
  //     type: responseData.type,
  //     role_id: responseData.role
  //   };

  //   // Validation check
  //   if (!accessToken || !refreshTokenValue) {
  //     console.error('Missing tokens in response:', { accessToken, refreshTokenValue });
  //     return;
  //   }

  //   // Store in localStorage
  //   localStorage.setItem('access_token', accessToken);
  //   localStorage.setItem('refresh_token', refreshTokenValue);
  //   localStorage.setItem('permissions', JSON.stringify(userPermissions));
  //   localStorage.setItem('role', JSON.stringify(userRole));
  //   localStorage.setItem('user', JSON.stringify(userData));

  //   // Update state
  //   setToken(accessToken);
  //   setRefreshToken(refreshTokenValue);
  //   setPermissions(userPermissions);
  //   setRole(userRole);
  //   setUser(userData);

  //   console.log('Login successful - Data stored:', {
  //     token: accessToken ? 'Present' : 'Missing',
  //     permissions: userPermissions.length,
  //     role: userRole?.name,
  //     user: userData.name
  //   });
  // };


  const login = (apiResponse) => {
    console.log('Login function called with response:', apiResponse);
    
    // Backend returns: { message: "Successful", data: {...}, count: null }
    // Extract data from the nested data object
    const responseData = apiResponse.data;
    
    if (!responseData) {
      console.error('No data in API response');
      return;
    }

    const accessToken = responseData.access_token;
    const refreshTokenValue = responseData.refresh_token;
    const userPermissions = responseData.permissions || {}; // Object, not array
    const userRoleId = responseData.role; // This is the ID (1)
    const roleName = responseData.role_name; // This is the name ("Super")
    
    const userData = {
      id: responseData.id,
      first_name: responseData.first_name,
      last_name: responseData.last_name,
      full_name: responseData.full_name,
      username: responseData.username,
      email: responseData.email,
      mobile: responseData.mobile,
      profile_image: responseData.profile_image,
      role_id: userRoleId,
      role_name: roleName,
      type: responseData.type,
      permissions: userPermissions // Include permissions in user data
    };

    // Create a role object with both ID and name
    const roleObject = {
      id: userRoleId,
      name: roleName
    };

    // Validation check
    if (!accessToken || !refreshTokenValue) {
      console.error('Missing tokens in response:', { accessToken, refreshTokenValue });
      return;
    }

    // Store in localStorage
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshTokenValue);
    localStorage.setItem('permissions', JSON.stringify(userPermissions));
    localStorage.setItem('role', JSON.stringify(roleObject));
    localStorage.setItem('user', JSON.stringify(userData));

    // Update state
    setToken(accessToken);
    setRefreshToken(refreshTokenValue);
    setPermissions(userPermissions);
    setRole(roleObject);
    setUser(userData);

    console.log('Login successful - Data stored:', {
      token: accessToken ? 'Present' : 'Missing',
      permissionsCount: Object.keys(userPermissions).length,
      role: roleObject,
      user: userData
    });
  };

  const logout = async () => {
    try {
      console.log('Attempting to logout...');
      
      // Backend expects logout data in the request body
      // Check LogoutSerializer to see what fields are needed
      await AxiosInstance.post('/api/user/v1/logout/', {
        // Add any required fields from LogoutSerializer here if needed
      });
      
      console.log('Logout API call successful');
    } catch (error) {
      console.error('Logout API error:', error);
    } finally {
      // Clear localStorage and state regardless of API call success
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('permissions');
      localStorage.removeItem('role');
      localStorage.removeItem('user');

      setToken(null);
      setRefreshToken(null);
      setPermissions([]);
      setRole(null);
      setUser(null);

      console.log('Logged out and cleared all data.');
      
      // Redirect to login page
      if (typeof window !== 'undefined') {
        window.location.href = '/Login';
      }
    }
  };

  // Helper function to check if user has a specific permission
  const hasPermission = (permission) => {
    const result = permissions.includes(permission);
    console.log(`Checking permission "${permission}":`, result);
    return result;
  };

  // Helper function to check multiple permissions (user needs at least one)
  const hasAnyPermission = (permissionList) => {
    const result = permissionList.some(permission => permissions.includes(permission));
    console.log(`Checking any permission from [${permissionList.join(', ')}]:`, result);
    return result;
  };

  // Helper function to check if user has all permissions
  const hasAllPermissions = (permissionList) => {
    const result = permissionList.every(permission => permissions.includes(permission));
    console.log(`Checking all permissions from [${permissionList.join(', ')}]:`, result);
    return result;
  };

  // Check if user is authenticated
  const isAuthenticated = !!token;

  // Check if user is superuser
  const isSuperuser = user?.is_superuser || false;

  return (
    <AuthContext.Provider 
      value={{ 
        token, 
        refreshToken,
        permissions, 
        role, 
        user,
        loading,
        login, 
        logout,
        hasPermission,
        hasAnyPermission,
        hasAllPermissions,
        isAuthenticated,
        isSuperuser
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

