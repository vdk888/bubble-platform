import React, { useState } from 'react';
import { LoginForm } from './LoginForm';
import { RegisterForm } from './RegisterForm';

export function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);

  console.log('🏠 AuthPage rendered, isLogin:', isLogin);

  return (
    <>
      {isLogin ? (
        <LoginForm onSwitchToRegister={() => {
          console.log('🔄 Switching to Register form');
          setIsLogin(false);
        }} />
      ) : (
        <RegisterForm onSwitchToLogin={() => {
          console.log('🔄 Switching to Login form');
          setIsLogin(true);
        }} />
      )}
    </>
  );
}