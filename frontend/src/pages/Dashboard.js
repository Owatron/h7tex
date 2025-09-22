import { useQuery, useMutation, gql } from '@apollo/client';
import { useAuth } from '../context/AuthContext';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeftOnRectangleIcon, PlusIcon, DocumentDuplicateIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import { useState } from 'react';

const GET_USER_DATA = gql`
  query CurrentUser {
    currentUser {
      id
      username
      workspaces {
        id
        name
        spreadsheets {
          id
          name
        }
      }
    }
  }
`;

const CREATE_WORKSPACE = gql`
    mutation CreateWorkspace($name: String!) {
        createWorkspace(name: $name) {
            workspace {
                id
                name
            }
        }
    }
`;

export default function Dashboard() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const { loading, error, data, refetch } = useQuery(GET_USER_DATA);
    const [newWorkspaceName, setNewWorkspaceName] = useState('');

    const [createWorkspace, { loading: creatingWorkspace }] = useMutation(CREATE_WORKSPACE, {
        onCompleted: () => {
            toast.success("Workspace created!");
            setNewWorkspaceName('');
            refetch();
        },
        onError: (err) => toast.error(err.message),
    });

    const handleCreateWorkspace = (e) => {
        e.preventDefault();
        if (newWorkspaceName.trim()) {
            createWorkspace({ variables: { name: newWorkspaceName.trim() } });
        }
    };
    
    if (loading) return <div className="flex justify-center items-center h-screen"><p>Loading...</p></div>;
    if (error) return <p>Error :(</p>;

    return (
        <div className="min-h-screen bg-slate-50">
            <header className="bg-white shadow-sm">
                <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8 flex justify-between items-center">
                    <h1 className="text-2xl font-bold text-slate-800">Welcome, {data.currentUser.username}</h1>
                    <button onClick={() => { logout(); navigate('/auth'); }} className="flex items-center text-sm font-medium text-slate-600 hover:text-blue-600">
                        Logout
                        <ArrowLeftOnRectangleIcon className="ml-2 h-5 w-5"/>
                    </button>
                </div>
            </header>
            <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
                <div className="px-4 py-6 sm:px-0">
                    <div className="mb-8">
                        <h2 className="text-xl font-semibold text-slate-700 mb-4">Your Workspaces</h2>
                        {data.currentUser.workspaces.map(ws => (
                            <div key={ws.id} className="bg-white rounded-xl shadow p-6 mb-4">
                                <h3 className="text-lg font-bold text-slate-800">{ws.name}</h3>
                                <p className="text-xs text-slate-400 mb-4">ID: {ws.id}</p>
                                <ul className="space-y-2">
                                    {ws.spreadsheets.map(sheet => (
                                        <li key={sheet.id}>
                                            <Link to={`/spreadsheet/${sheet.id}`} className="flex items-center text-blue-600 hover:text-blue-800 hover:bg-blue-50 p-2 rounded-md transition-colors">
                                                <DocumentDuplicateIcon className="h-5 w-5 mr-3"/>
                                                {sheet.name}
                                            </Link>
                                        </li>
                                    ))}
                                    {ws.spreadsheets.length === 0 && <p className="text-slate-500 text-sm">No spreadsheets yet.</p>}
                                </ul>
                                 <Link to={`/spreadsheet/new?ws=${ws.id}`} className="mt-4 inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none">
                                    <PlusIcon className="-ml-0.5 mr-2 h-4 w-4" />
                                    New Spreadsheet
                                </Link>
                            </div>
                        ))}
                    </div>
                    <div className="bg-white rounded-xl shadow p-6">
                         <h3 className="text-lg font-bold text-slate-800 mb-3">Create New Workspace</h3>
                        <form onSubmit={handleCreateWorkspace} className="flex space-x-2">
                            <input
                                type="text"
                                value={newWorkspaceName}
                                onChange={(e) => setNewWorkspaceName(e.target.value)}
                                placeholder="New workspace name"
                                className="flex-grow px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                            <button type="submit" disabled={creatingWorkspace} className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300">
                                Create
                            </button>
                        </form>
                    </div>
                </div>
            </main>
        </div>
    );
}

