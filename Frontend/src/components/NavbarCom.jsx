// 'use client';
// import React from 'react';
// import Link from 'next/link';
// import { usePathname } from 'next/navigation';

// const NavbarCom = () => {
//   const pathname = usePathname();

//   const navItems = [
//     { name: 'Home', path: '/' },
//     { name: 'Blogs', path: '/blogs' },
//     { name: 'About', path: '/about' },
//     { name: 'Services', path: '/services' },
//     { name: 'Contact', path: '/contact' },
//   ];

//   return (
//     <nav className="w-full bg-gradient-to-r from-gray-900 via-black to-gray-900 backdrop-blur-md shadow-[0_3px_10px_rgba(0,0,0,0.4)]">
//       <div className="container mx-auto flex justify-between items-center py-2 px-8">
//         {/* Brand Name */}
//         <div
//           className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-yellow-600 font-serif text-2xl tracking-[0.15em] uppercase hover:scale-105 transition-transform duration-300"
//           style={{ fontFamily: "'Playfair Display', 'Georgia', serif" }}
//         >
//           <Link href="/">AI Blogs</Link>
//         </div>

//         {/* Nav Links - Centered */}
//         <ul className="absolute left-1/2 transform -translate-x-1/2 flex items-center space-x-10">
//           {navItems.map((item) => {
//             const isActive = pathname === item.path;
//             return (
//               <li key={item.path} className="relative group">
//                 <Link href={item.path}>
//                   <span
//                     className={`transition-all duration-300 font-serif text-base tracking-wider ${
//                       isActive
//                         ? 'text-amber-400 font-semibold'
//                         : 'text-gray-200 hover:text-amber-300'
//                     }`}
//                     style={{ fontFamily: "'Cormorant Garamond', 'Playfair Display', serif" }}
//                   >
//                     {item.name}
//                   </span>
//                 </Link>
//                 {/* Animated underline */}
//                 <span
//                   className={`absolute left-0 -bottom-1 h-[2px] rounded-full transition-all duration-300 ${
//                     isActive
//                       ? 'w-full bg-amber-400'
//                       : 'w-0 bg-amber-300 group-hover:w-full'
//                   }`}
//                 ></span>
//               </li>
//             );
//           })}
//         </ul>

//         {/* Spacer for layout balance */}
//         <div className="w-32"></div>
//       </div>

//       {/* Elegant Glow Line */}
//       <div className="h-[1px] w-full bg-gradient-to-r from-amber-500 via-yellow-400 to-amber-500"></div>
//     </nav>
//   );
// };

// export default NavbarCom;





'use client';
import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NavbarCom = ({ isSticky }) => {
  const pathname = usePathname();

  const navItems = [
    { name: 'Home', path: '/' },
    { name: 'Blogs', path: '/blogs' },
    { name: 'About', path: '/about' },
    { name: 'Services', path: '/services' },
    { name: 'Contact', path: '/contact' },
  ];

  return (
    <nav className={`w-full bg-gradient-to-r from-gray-900 via-black to-gray-900 backdrop-blur-md shadow-[0_3px_10px_rgba(0,0,0,0.4)] transition-all duration-300 ${
      isSticky ? 'fixed top-0 left-0 right-0 z-50 shadow-2xl' : 'relative'
    }`}>
      <div className="container mx-auto flex justify-between items-center py-2 px-8">
        {/* Brand Name */}
        <div
          className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-yellow-600 font-serif text-2xl tracking-[0.15em] uppercase hover:scale-105 transition-transform duration-300"
          style={{ fontFamily: "'Playfair Display', 'Georgia', serif" }}
        >
          <Link href="/">AI Blogs</Link>
        </div>

        {/* Nav Links - Centered */}
        <ul className="absolute left-1/2 transform -translate-x-1/2 flex items-center space-x-10">
          {navItems.map((item) => {
            const isActive = pathname === item.path;
            return (
              <li key={item.path} className="relative group">
                <Link href={item.path}>
                  <span
                    className={`transition-all duration-300 font-serif text-base tracking-wider ${
                      isActive
                        ? 'text-amber-400 font-semibold'
                        : 'text-gray-200 hover:text-amber-300'
                    }`}
                    style={{ fontFamily: "'Cormorant Garamond', 'Playfair Display', serif" }}
                  >
                    {item.name}
                  </span>
                </Link>
                {/* Animated underline */}
                <span
                  className={`absolute left-0 -bottom-1 h-[2px] rounded-full transition-all duration-300 ${
                    isActive
                      ? 'w-full bg-amber-400'
                      : 'w-0 bg-amber-300 group-hover:w-full'
                  }`}
                ></span>
              </li>
            );
          })}
        </ul>

        {/* Spacer for layout balance */}
        <div className="w-32"></div>
      </div>

      {/* Elegant Glow Line */}
      <div className="h-[1px] w-full bg-gradient-to-r from-amber-500 via-yellow-400 to-amber-500"></div>
    </nav>
  );
};

export default NavbarCom;