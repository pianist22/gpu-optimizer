import { Github, Twitter, Mail } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="bg-white border-t">
      <div className="max-w-7xl mx-auto py-12 px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div>
            <h3 className="text-lg font-bold text-black mb-4">GPU Optimizer</h3>
            <p className="text-gray-600 text-sm">
              Advanced GPU optimization tool for gamers and professionals.
            </p>
          </div>
          
          <div>
            <h3 className="text-lg font-semibold text-black mb-4">Quick Links</h3>
            <ul className="space-y-2">
              <li><a href="#" className="text-gray-600 hover:text-indigo-600 text-sm">Documentation</a></li>
              <li><a href="#" className="text-gray-600 hover:text-indigo-600 text-sm">Support</a></li>
              <li><a href="#" className="text-gray-600 hover:text-indigo-600 text-sm">Privacy Policy</a></li>
            </ul>
          </div>
          
          <div>
            <h3 className="text-lg font-semibold  text-black mb-4">Connect</h3>
            <div className="flex space-x-4">
              <a href="#" className="text-gray-400 hover:text-indigo-600 transition-colors">
                <Github className="h-5 w-5" />
              </a>
              <a href="#" className="text-gray-400 hover:text-indigo-600 transition-colors">
                <Twitter className="h-5 w-5" />
              </a>
              <a href="#" className="text-gray-400 hover:text-indigo-600 transition-colors">
                <Mail className="h-5 w-5" />
              </a>
            </div>
          </div>
        </div>
        
        <div className="mt-8 pt-8 border-t text-center text-sm text-gray-500">
          © {new Date().getFullYear()} GPU Optimizer. All rights reserved.
        </div>
      </div>
    </footer>
  );
}