'use client';

import { motion } from 'framer-motion';
import { Zap, Settings, Gauge } from 'lucide-react';

export default function HeroSection() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-indigo-50 to-white py-24 px-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="max-w-7xl mx-auto text-center"
      >
        <h2 className="text-5xl font-bold mb-6 bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-purple-600">
          Optimize Your GPU Usage
        </h2>
        <p className="text-xl text-gray-600 mb-12 max-w-2xl mx-auto">
          Maximize performance and efficiency with our intelligent GPU optimization tool.
          Get the perfect balance of power and performance for your needs.
        </p>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto mt-16">
          {[
            { icon: Zap, title: 'Faster Performance', desc: 'Up to 25% speed increase' },
            { icon: Settings, title: 'Smart Optimization', desc: 'AI-powered settings' },
            { icon: Gauge, title: 'Real-time Monitoring', desc: 'Track GPU metrics live' }
          ].map((feature, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: index * 0.2 }}
              className="bg-white rounded-2xl p-6 shadow-xl shadow-indigo-100"
            >
              <feature.icon className="h-10 w-10 text-indigo-600 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2 text-black">{feature.title}</h3>
              <p className="text-gray-500">{feature.desc}</p>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </section>
  );
}