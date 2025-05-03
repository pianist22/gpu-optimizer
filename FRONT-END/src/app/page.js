import Navbar from '../components/Navbar';
import HeroSection from '../components/HeroSection';
import OptionsForm from '../components/OptionsForm';
import Footer from '../components/Footer';
// import * from './global.css'

export default function Home() {
  return (
    <div className='bg-richblack-900' >
      <Navbar />
      <HeroSection />
      <OptionsForm />
      <Footer />
    </div>
  );
}
