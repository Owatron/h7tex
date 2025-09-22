import { useState } from 'react';
import { useMutation } from '@apollo/client';
import { gql } from '@apollo/client';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';
import { ShieldCheckIcon } from '@heroicons/react/24/outline';

const LOGIN_MUTATION = gql`
  mutation TokenAuth($username: String!, $password: String!) {
    tokenAuth(username: $username, password: $password) {
      token
    }
  }
`;

const SIGNUP_MUTATION = gql`
  mutation CreateUser($username: String!, $email: String!, $password: String!) {
    createUser(username: $username, email: $email, password: $password) {
      token
      user {
        id
        username
      }
    }
  }
`;


export default function Auth() {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const { login } = useAuth();

  const [loginUser, { loading: loginLoading }] = useMutation(LOGIN_MUTATION, {
    onCompleted: (data) => {
      login(data.tokenAuth.token);
      toast.success('Logged in successfully!');
    },
    onError: (error) => toast.error(error.message),
  });
  
  const [signupUser, { loading: signupLoading }] = useMutation(SIGNUP_MUTATION, {
    onCompleted: (data) => {
        login(data.createUser.token);
        toast.success('Account created successfully!');
    },
    onError: (error) => toast.error(error.message),
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (isLogin) {
      loginUser({ variables: { username, password } });
    } else {
      signupUser({ variables: { username, email, password } });
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col justify-center items-center">
      <div className="max-w-md w-full mx-auto">
        <div className="flex justify-center items-center mb-6">
            <ShieldCheckIcon className="h-12 w-12 text-blue-600"/>
            <h1 className="text-4xl font-bold text-slate-800 ml-3">SyncGrid</h1>
        </div>
        <div className="bg-white p-8 rounded-2xl shadow-lg">
          <h2 className="text-2xl font-bold text-center text-slate-700 mb-1">{isLogin ? 'Welcome Back!' : 'Create Account'}</h2>
          <p className="text-center text-slate-500 mb-6">{isLogin ? 'Sign in to continue' : 'Get started with a new account'}</p>
          <form onSubmit={handleSubmit}>
            <div className="space-y-4">
              <input
                type="text"
                placeholder="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
              {!isLogin && (
                <input
                  type="email"
                  placeholder="Email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              )}
              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            <button
              type="submit"
              disabled={loginLoading || signupLoading}
              className="w-full mt-6 bg-blue-600 text-white font-bold py-3 px-4 rounded-lg hover:bg-blue-700 transition-colors disabled:bg-blue-300"
            >
              {loginLoading || signupLoading ? 'Processing...' : (isLogin ? 'Login' : 'Sign Up')}
            </button>
          </form>
          <p className="text-center text-sm text-slate-500 mt-6">
            {isLogin ? "Don't have an account?" : 'Already have an account?'}
            <button onClick={() => setIsLogin(!isLogin)} className="font-semibold text-blue-600 hover:text-blue-700 ml-1">
              {isLogin ? 'Sign Up' : 'Login'}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}

