import { Cpu, Menu } from 'lucide-react';

export default function Navbar() {
  return (
    <nav className="sticky top-0 z-50 backdrop-blur-lg bg-white/80 shadow-sm px-6 lg:px-8 py-4">
      <div className="max-w-7xl mx-auto flex justify-between items-center">
        <div className="flex items-center space-x-2">
          <Cpu className="h-8 w-8 text-indigo-600" />
          <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-purple-600">
            GPU Optimizer
          </h1>
        </div>
        
        <div className="hidden sm:flex items-center space-x-8">
          <a href="#features" className="text-gray-600 hover:text-indigo-600 transition-colors">
            Features
          </a>
          <a href="#about" className="text-gray-600 hover:text-indigo-600 transition-colors">
            About
          </a>
          <button className="px-6 py-2 rounded-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-medium hover:shadow-lg hover:opacity-90 transition-all">
            Login
          </button>
        </div>
        
        <button className="sm:hidden text-gray-600">
          <Menu className="h-6 w-6" />
        </button>
      </div>
    </nav>
  );
}
  