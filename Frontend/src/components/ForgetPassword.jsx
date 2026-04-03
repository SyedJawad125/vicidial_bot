// 'use client';
// import { useState } from "react";
// import { useRouter } from 'next/navigation';
// import AxiosInstance from "@/components/AxiosInstance";
// import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
// import { faEye, faEyeSlash, faArrowLeft } from '@fortawesome/free-solid-svg-icons';
// import { ToastContainer, toast } from 'react-toastify';
// import 'react-toastify/dist/ReactToastify.css';

// export default function ForgetPassword() {
//     const router = useRouter();

//     const [email, setEmail] = useState("");
//     const [otp, setOtp] = useState("");
//     const [newPassword, setNewPassword] = useState("");
//     const [confirmPassword, setConfirmPassword] = useState("");
//     const [step, setStep] = useState(1);
//     const [showPassword, setShowPassword] = useState(false);
//     const [loading, setLoading] = useState(false);

//     const handleForgetPassword = async () => {
//         if (!email) {
//             toast.error("Please enter your email address");
//             return;
//         }

//         const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
//         if (!emailRegex.test(email)) {
//             toast.error("Please enter a valid email address");
//             return;
//         }

//         setLoading(true);
//         try {
//             const response = await AxiosInstance.post('/user/forget-password', { email });
//             console.log("Email sent successfully:", response);
//             toast.success("OTP sent to your email!");
//             setStep(2);
//         } catch (error) {
//             console.error("Error sending email:", error.response?.data || error.message);
//             toast.error("Failed to send OTP. Please try again.");
//         } finally {
//             setLoading(false);
//         }
//     };

//     const handleVerifyOtp = async () => {
//         if (!otp || !newPassword || !confirmPassword) {
//             toast.error("Please fill in all fields");
//             return;
//         }

//         if (newPassword !== confirmPassword) {
//             toast.error("Passwords do not match");
//             return;
//         }

//         if (newPassword.length < 6) {
//             toast.error("Password must be at least 6 characters");
//             return;
//         }

//         setLoading(true);
//         try {
//             const response = await AxiosInstance.post('/user/verify-otp', {
//                 otp,
//                 new_password: newPassword,
//                 confirm_password: confirmPassword,
//             });
//             console.log("OTP verified successfully:", response);

//             toast.success("Password reset successful!", {
//                 onClose: () => {
//                     router.push("/Login");
//                 },
//             });

//             setOtp("");
//             setNewPassword("");
//             setConfirmPassword("");
//         } catch (error) {
//             console.error("Error verifying OTP:", error.response?.data || error.message);
//             toast.error("Failed to verify OTP. Please try again.");
//         } finally {
//             setLoading(false);
//         }
//     };

//     const handleback = () => {
//         if (step === 2) {
//             setStep(1);
//         } else {
//             router.push("/Login");
//         }
//     };

//     return (
//         <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
//             {/* Animated background elements */}
//             <div className="absolute inset-0 overflow-hidden">
//                 <div className="absolute -inset-10 opacity-20">
//                     <div className="absolute top-1/4 left-1/4 w-72 h-72 bg-gradient-to-r from-amber-400 to-orange-500 rounded-full blur-3xl animate-pulse"></div>
//                     <div className="absolute bottom-1/4 right-1/4 w-72 h-72 bg-gradient-to-r from-cyan-400 to-blue-500 rounded-full blur-3xl animate-pulse delay-1000"></div>
//                 </div>
//             </div>

//             <div className="relative bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
//                 {/* Decorative header */}
//                 <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-amber-400 via-rose-500 to-cyan-400"></div>
                
//                 <div className="p-8">
//                     {/* Back Button */}
//                     <button 
//                         onClick={handleback} 
//                         className="mb-6 text-white/70 hover:text-white transition-colors duration-300 flex items-center group"
//                     >
//                         <FontAwesomeIcon icon={faArrowLeft} className="mr-2 group-hover:-translate-x-1 transition-transform duration-300" />
//                         <span>Back</span>
//                     </button>

//                     {/* Logo/Brand */}
//                     <div className="text-center mb-8">
//                         <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-amber-400 to-orange-500 rounded-2xl shadow-lg mb-4">
//                             <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//                                 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
//                             </svg>
//                         </div>
//                         <h2 className="text-3xl font-light text-white tracking-wide">
//                             {step === 1 ? "Forgot Password" : "Verify OTP"}
//                         </h2>
//                         <p className="text-white/60 text-sm mt-2 font-light">
//                             {step === 1 ? "Enter your email to receive OTP" : "Enter OTP and set new password"}
//                         </p>
//                     </div>

//                     {step === 1 ? (
//                         <div className="space-y-6">
//                             {/* Email Field */}
//                             <div className="group">
//                                 <label 
//                                     htmlFor="email" 
//                                     className="block text-sm font-medium text-white/80 mb-2 transition-all duration-300 group-focus-within:text-amber-300"
//                                 >
//                                     Email Address
//                                 </label>
//                                 <div className="relative">
//                                     <input
//                                         type="email"
//                                         id="email"
//                                         className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-amber-400/50 focus:border-amber-400/30 transition-all duration-300 backdrop-blur-sm"
//                                         placeholder="Enter your email"
//                                         value={email}
//                                         onChange={(e) => setEmail(e.target.value)}
//                                         disabled={loading}
//                                     />
//                                     <div className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/40">
//                                         <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//                                             <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
//                                         </svg>
//                                     </div>
//                                 </div>
//                             </div>

//                             {/* Send OTP Button */}
//                             <button
//                                 onClick={handleForgetPassword}
//                                 disabled={loading}
//                                 className={`w-full py-4 px-6 rounded-xl font-medium text-white transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] ${
//                                     loading 
//                                         ? 'bg-gray-500 cursor-not-allowed' 
//                                         : 'bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 shadow-lg hover:shadow-amber-500/25'
//                                 }`}
//                             >
//                                 {loading ? (
//                                     <span className="flex items-center justify-center">
//                                         <svg className="animate-spin h-5 w-5 mr-3" viewBox="0 0 24 24">
//                                             <circle 
//                                                 className="opacity-25" 
//                                                 cx="12" 
//                                                 cy="12" 
//                                                 r="10" 
//                                                 stroke="currentColor" 
//                                                 strokeWidth="4"
//                                                 fill="none"
//                                             />
//                                             <path 
//                                                 className="opacity-75" 
//                                                 fill="currentColor" 
//                                                 d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
//                                             />
//                                         </svg>
//                                         Sending OTP...
//                                     </span>
//                                 ) : (
//                                     'Send OTP'
//                                 )}
//                             </button>
//                         </div>
//                     ) : (
//                         <div className="space-y-6">
//                             {/* OTP Field */}
//                             <div className="group">
//                                 <label 
//                                     htmlFor="otp" 
//                                     className="block text-sm font-medium text-white/80 mb-2 transition-all duration-300 group-focus-within:text-amber-300"
//                                 >
//                                     OTP Code
//                                 </label>
//                                 <div className="relative">
//                                     <input
//                                         type="text"
//                                         id="otp"
//                                         className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-amber-400/50 focus:border-amber-400/30 transition-all duration-300 backdrop-blur-sm"
//                                         placeholder="Enter OTP"
//                                         value={otp}
//                                         onChange={(e) => setOtp(e.target.value)}
//                                         disabled={loading}
//                                     />
//                                     <div className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/40">
//                                         <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//                                             <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
//                                         </svg>
//                                     </div>
//                                 </div>
//                             </div>

//                             {/* New Password Field */}
//                             <div className="group">
//                                 <label 
//                                     htmlFor="newPassword" 
//                                     className="block text-sm font-medium text-white/80 mb-2 transition-all duration-300 group-focus-within:text-cyan-300"
//                                 >
//                                     New Password
//                                 </label>
//                                 <div className="relative">
//                                     <input
//                                         type={showPassword ? "text" : "password"}
//                                         id="newPassword"
//                                         className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-cyan-400/50 focus:border-cyan-400/30 transition-all duration-300 backdrop-blur-sm pr-12"
//                                         placeholder="Enter new password"
//                                         value={newPassword}
//                                         onChange={(e) => setNewPassword(e.target.value)}
//                                         disabled={loading}
//                                     />
//                                     <button
//                                         type="button"
//                                         onClick={() => setShowPassword(!showPassword)}
//                                         className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/40 hover:text-white/60 transition-colors duration-300"
//                                     >
//                                         <FontAwesomeIcon icon={showPassword ? faEyeSlash : faEye} className="w-5 h-5" />
//                                     </button>
//                                 </div>
//                             </div>

//                             {/* Confirm Password Field */}
//                             <div className="group">
//                                 <label 
//                                     htmlFor="confirmPassword" 
//                                     className="block text-sm font-medium text-white/80 mb-2 transition-all duration-300 group-focus-within:text-cyan-300"
//                                 >
//                                     Confirm Password
//                                 </label>
//                                 <div className="relative">
//                                     <input
//                                         type={showPassword ? "text" : "password"}
//                                         id="confirmPassword"
//                                         className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-cyan-400/50 focus:border-cyan-400/30 transition-all duration-300 backdrop-blur-sm pr-12"
//                                         placeholder="Confirm new password"
//                                         value={confirmPassword}
//                                         onChange={(e) => setConfirmPassword(e.target.value)}
//                                         disabled={loading}
//                                     />
//                                     <button
//                                         type="button"
//                                         onClick={() => setShowPassword(!showPassword)}
//                                         className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/40 hover:text-white/60 transition-colors duration-300"
//                                     >
//                                         <FontAwesomeIcon icon={showPassword ? faEyeSlash : faEye} className="w-5 h-5" />
//                                     </button>
//                                 </div>
//                             </div>

//                             {/* Reset Password Button */}
//                             <button
//                                 onClick={handleVerifyOtp}
//                                 disabled={loading}
//                                 className={`w-full py-4 px-6 rounded-xl font-medium text-white transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] ${
//                                     loading 
//                                         ? 'bg-gray-500 cursor-not-allowed' 
//                                         : 'bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 shadow-lg hover:shadow-cyan-500/25'
//                                 }`}
//                             >
//                                 {loading ? (
//                                     <span className="flex items-center justify-center">
//                                         <svg className="animate-spin h-5 w-5 mr-3" viewBox="0 0 24 24">
//                                             <circle 
//                                                 className="opacity-25" 
//                                                 cx="12" 
//                                                 cy="12" 
//                                                 r="10" 
//                                                 stroke="currentColor" 
//                                                 strokeWidth="4"
//                                                 fill="none"
//                                             />
//                                             <path 
//                                                 className="opacity-75" 
//                                                 fill="currentColor" 
//                                                 d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
//                                             />
//                                         </svg>
//                                         Resetting Password...
//                                     </span>
//                                 ) : (
//                                     'Reset Password'
//                                 )}
//                             </button>
//                         </div>
//                     )}

//                     {/* Sign In Link */}
//                     <div className="text-center mt-8">
//                         <span className="text-white/60 text-sm">
//                             Remember your password?{' '}
//                         </span>
//                         <button
//                             onClick={() => router.push("/Login")}
//                             className="text-sm text-cyan-300 hover:text-cyan-200 transition-colors duration-300 font-medium hover:underline"
//                         >
//                             Sign in
//                         </button>
//                     </div>
//                 </div>
//             </div>
//             <ToastContainer 
//                 position="top-right"
//                 autoClose={3000}
//                 hideProgressBar={false}
//                 newestOnTop={false}
//                 closeOnClick
//                 rtl={false}
//                 pauseOnFocusLoss
//                 draggable
//                 pauseOnHover
//                 theme="dark"
//             />
//         </div>
//     );
// }



'use client';
import { useState } from "react";
import { useRouter } from 'next/navigation';
import AxiosInstance from "@/components/AxiosInstance";
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faEye, faEyeSlash, faArrowLeft } from '@fortawesome/free-solid-svg-icons';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

export default function ForgetPassword() {
    const router = useRouter();

    const [email, setEmail] = useState("");
    const [otp, setOtp] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [step, setStep] = useState(1);
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const [resetToken, setResetToken] = useState(""); // Store the reset token from step 2

    // Step 1: Request OTP
    const handleForgetPassword = async () => {
        if (!email) {
            toast.error("Please enter your email address");
            return;
        }

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            toast.error("Please enter a valid email address");
            return;
        }

        setLoading(true);
        try {
            const response = await AxiosInstance.post('/api/user/v1/forget/password/', { email });
            console.log("OTP sent successfully:", response);
            toast.success("OTP sent to your email!");
            setStep(2);
        } catch (error) {
            console.error("Error sending OTP:", error.response?.data || error.message);
            const errorMessage = error.response?.data?.message || "Failed to send OTP. Please try again.";
            toast.error(errorMessage);
        } finally {
            setLoading(false);
        }
    };

    // Step 2: Verify OTP and get reset token
    const handleVerifyOtp = async () => {
        if (!otp) {
            toast.error("Please enter the OTP code");
            return;
        }

        setLoading(true);
        try {
            const response = await AxiosInstance.post('/api/user/v1/verify/otp/', {
                email,
                code: otp,
            });
            console.log("OTP verified successfully:", response);
            
            // Store the reset token for step 3
            setResetToken(response.data.reset_token);
            toast.success("OTP verified! Please set your new password.");
            setStep(3);
        } catch (error) {
            console.error("Error verifying OTP:", error.response?.data || error.message);
            const errorMessage = error.response?.data?.message || "Failed to verify OTP. Please try again.";
            toast.error(errorMessage);
        } finally {
            setLoading(false);
        }
    };

    // Step 3: Reset password using the reset token
    const handleResetPassword = async () => {
        if (!newPassword || !confirmPassword) {
            toast.error("Please fill in all fields");
            return;
        }

        if (newPassword !== confirmPassword) {
            toast.error("Passwords do not match");
            return;
        }

        if (newPassword.length < 6) {
            toast.error("Password must be at least 6 characters");
            return;
        }

        setLoading(true);
        try {
            const response = await AxiosInstance.post('/api/user/v1/reset/password/', {
                reset_token: resetToken,
                new_password: newPassword,
                confirm_password: confirmPassword,
            });
            console.log("Password reset successfully:", response);

            toast.success("Password reset successful!", {
                onClose: () => {
                    router.push("/Login");
                },
            });

            // Clear all fields
            setOtp("");
            setNewPassword("");
            setConfirmPassword("");
            setResetToken("");
        } catch (error) {
            console.error("Error resetting password:", error.response?.data || error.message);
            const errorMessage = error.response?.data?.message || "Failed to reset password. Please try again.";
            toast.error(errorMessage);
        } finally {
            setLoading(false);
        }
    };

    const handleback = () => {
        if (step === 3) {
            setStep(2);
        } else if (step === 2) {
            setStep(1);
        } else {
            router.push("/Login");
        }
    };

    // Get step title and description
    const getStepInfo = () => {
        switch(step) {
            case 1:
                return {
                    title: "Forgot Password",
                    description: "Enter your email to receive OTP"
                };
            case 2:
                return {
                    title: "Verify OTP",
                    description: "Enter the 6-digit code sent to your email"
                };
            case 3:
                return {
                    title: "Reset Password",
                    description: "Set your new password"
                };
            default:
                return {
                    title: "Forgot Password",
                    description: "Reset your password"
                };
        }
    };

    // Progress indicator
    const renderProgressBar = () => {
        const steps = ['Email', 'Verify OTP', 'New Password'];
        
        return (
            <div className="mb-8">
                <div className="flex justify-between items-center mb-4">
                    {steps.map((stepName, index) => (
                        <div key={index} className="flex flex-col items-center">
                            <div className={`w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300 ${
                                index + 1 < step 
                                    ? 'bg-green-500 text-white' 
                                    : index + 1 === step
                                    ? 'bg-amber-500 text-white'
                                    : 'bg-white/10 text-white/40'
                            }`}>
                                {index + 1}
                            </div>
                            <span className={`text-xs mt-2 transition-all duration-300 ${
                                index + 1 <= step ? 'text-white' : 'text-white/40'
                            }`}>
                                {stepName}
                            </span>
                        </div>
                    ))}
                </div>
                <div className="relative h-2 bg-white/10 rounded-full">
                    <div 
                        className="absolute h-full bg-gradient-to-r from-amber-400 via-rose-500 to-cyan-400 rounded-full transition-all duration-500"
                        style={{ width: `${((step - 1) / (steps.length - 1)) * 100}%` }}
                    ></div>
                </div>
            </div>
        );
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
            {/* Animated background elements */}
            <div className="absolute inset-0 overflow-hidden">
                <div className="absolute -inset-10 opacity-20">
                    <div className="absolute top-1/4 left-1/4 w-72 h-72 bg-gradient-to-r from-amber-400 to-orange-500 rounded-full blur-3xl animate-pulse"></div>
                    <div className="absolute bottom-1/4 right-1/4 w-72 h-72 bg-gradient-to-r from-cyan-400 to-blue-500 rounded-full blur-3xl animate-pulse delay-1000"></div>
                </div>
            </div>

            <div className="relative bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
                {/* Decorative header */}
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-amber-400 via-rose-500 to-cyan-400"></div>
                
                <div className="p-8">
                    {/* Back Button */}
                    <button 
                        onClick={handleback} 
                        className="mb-6 text-white/70 hover:text-white transition-colors duration-300 flex items-center group"
                    >
                        <FontAwesomeIcon icon={faArrowLeft} className="mr-2 group-hover:-translate-x-1 transition-transform duration-300" />
                        <span>Back</span>
                    </button>

                    {/* Logo/Brand */}
                    <div className="text-center mb-8">
                        <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-amber-400 to-orange-500 rounded-2xl shadow-lg mb-4">
                            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                            </svg>
                        </div>
                        <h2 className="text-3xl font-light text-white tracking-wide">
                            {getStepInfo().title}
                        </h2>
                        <p className="text-white/60 text-sm mt-2 font-light">
                            {getStepInfo().description}
                        </p>
                    </div>

                    {/* Progress Bar */}
                    {renderProgressBar()}

                    {/* Step 1: Email Input */}
                    {step === 1 && (
                        <div className="space-y-6">
                            {/* Email Field */}
                            <div className="group">
                                <label 
                                    htmlFor="email" 
                                    className="block text-sm font-medium text-white/80 mb-2 transition-all duration-300 group-focus-within:text-amber-300"
                                >
                                    Email Address
                                </label>
                                <div className="relative">
                                    <input
                                        type="email"
                                        id="email"
                                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-amber-400/50 focus:border-amber-400/30 transition-all duration-300 backdrop-blur-sm"
                                        placeholder="Enter your email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        disabled={loading}
                                    />
                                    <div className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/40">
                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
                                        </svg>
                                    </div>
                                </div>
                            </div>

                            {/* Send OTP Button */}
                            <button
                                onClick={handleForgetPassword}
                                disabled={loading}
                                className={`w-full py-4 px-6 rounded-xl font-medium text-white transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] ${
                                    loading 
                                        ? 'bg-gray-500 cursor-not-allowed' 
                                        : 'bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 shadow-lg hover:shadow-amber-500/25'
                                }`}
                            >
                                {loading ? (
                                    <span className="flex items-center justify-center">
                                        <svg className="animate-spin h-5 w-5 mr-3" viewBox="0 0 24 24">
                                            <circle 
                                                className="opacity-25" 
                                                cx="12" 
                                                cy="12" 
                                                r="10" 
                                                stroke="currentColor" 
                                                strokeWidth="4"
                                                fill="none"
                                            />
                                            <path 
                                                className="opacity-75" 
                                                fill="currentColor" 
                                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                            />
                                        </svg>
                                        Sending OTP...
                                    </span>
                                ) : (
                                    'Send OTP'
                                )}
                            </button>
                        </div>
                    )}

                    {/* Step 2: OTP Verification */}
                    {step === 2 && (
                        <div className="space-y-6">
                            {/* Email Display (Read-only) */}
                            <div className="group">
                                <label className="block text-sm font-medium text-white/80 mb-2">
                                    Email Address
                                </label>
                                <div className="relative">
                                    <input
                                        type="email"
                                        className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white/80 cursor-not-allowed backdrop-blur-sm"
                                        value={email}
                                        readOnly
                                    />
                                    <div className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/40">
                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
                                        </svg>
                                    </div>
                                </div>
                            </div>

                            {/* OTP Field */}
                            <div className="group">
                                <label 
                                    htmlFor="otp" 
                                    className="block text-sm font-medium text-white/80 mb-2 transition-all duration-300 group-focus-within:text-cyan-300"
                                >
                                    6-digit OTP Code
                                </label>
                                <div className="relative">
                                    <input
                                        type="text"
                                        id="otp"
                                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-cyan-400/50 focus:border-cyan-400/30 transition-all duration-300 backdrop-blur-sm text-center text-2xl tracking-widest"
                                        placeholder="000000"
                                        value={otp}
                                        onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                                        disabled={loading}
                                        maxLength={6}
                                    />
                                    <div className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/40">
                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                                        </svg>
                                    </div>
                                </div>
                                <p className="text-xs text-white/40 mt-2">
                                    Enter the 6-digit code sent to your email
                                </p>
                            </div>

                            {/* Verify OTP Button */}
                            <button
                                onClick={handleVerifyOtp}
                                disabled={loading || otp.length !== 6}
                                className={`w-full py-4 px-6 rounded-xl font-medium text-white transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] ${
                                    loading || otp.length !== 6
                                        ? 'bg-gray-500 cursor-not-allowed' 
                                        : 'bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 shadow-lg hover:shadow-cyan-500/25'
                                }`}
                            >
                                {loading ? (
                                    <span className="flex items-center justify-center">
                                        <svg className="animate-spin h-5 w-5 mr-3" viewBox="0 0 24 24">
                                            <circle 
                                                className="opacity-25" 
                                                cx="12" 
                                                cy="12" 
                                                r="10" 
                                                stroke="currentColor" 
                                                strokeWidth="4"
                                                fill="none"
                                            />
                                            <path 
                                                className="opacity-75" 
                                                fill="currentColor" 
                                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                            />
                                        </svg>
                                        Verifying...
                                    </span>
                                ) : (
                                    'Verify OTP'
                                )}
                            </button>
                        </div>
                    )}

                    {/* Step 3: Reset Password */}
                    {step === 3 && (
                        <div className="space-y-6">
                            {/* New Password Field */}
                            <div className="group">
                                <label 
                                    htmlFor="newPassword" 
                                    className="block text-sm font-medium text-white/80 mb-2 transition-all duration-300 group-focus-within:text-green-300"
                                >
                                    New Password
                                </label>
                                <div className="relative">
                                    <input
                                        type={showPassword ? "text" : "password"}
                                        id="newPassword"
                                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-green-400/50 focus:border-green-400/30 transition-all duration-300 backdrop-blur-sm pr-12"
                                        placeholder="Enter new password"
                                        value={newPassword}
                                        onChange={(e) => setNewPassword(e.target.value)}
                                        disabled={loading}
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/40 hover:text-white/60 transition-colors duration-300"
                                    >
                                        <FontAwesomeIcon icon={showPassword ? faEyeSlash : faEye} className="w-5 h-5" />
                                    </button>
                                </div>
                            </div>

                            {/* Confirm Password Field */}
                            <div className="group">
                                <label 
                                    htmlFor="confirmPassword" 
                                    className="block text-sm font-medium text-white/80 mb-2 transition-all duration-300 group-focus-within:text-green-300"
                                >
                                    Confirm Password
                                </label>
                                <div className="relative">
                                    <input
                                        type={showPassword ? "text" : "password"}
                                        id="confirmPassword"
                                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-green-400/50 focus:border-green-400/30 transition-all duration-300 backdrop-blur-sm pr-12"
                                        placeholder="Confirm new password"
                                        value={confirmPassword}
                                        onChange={(e) => setConfirmPassword(e.target.value)}
                                        disabled={loading}
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/40 hover:text-white/60 transition-colors duration-300"
                                    >
                                        <FontAwesomeIcon icon={showPassword ? faEyeSlash : faEye} className="w-5 h-5" />
                                    </button>
                                </div>
                            </div>

                            {/* Password requirements */}
                            <div className="bg-white/5 rounded-xl p-4">
                                <p className="text-sm text-white/60 mb-2">Password requirements:</p>
                                <ul className="text-xs text-white/40 space-y-1">
                                    <li className={`flex items-center ${newPassword.length >= 6 ? 'text-green-400' : ''}`}>
                                        <svg className={`w-4 h-4 mr-2 ${newPassword.length >= 6 ? 'text-green-400' : 'text-white/20'}`} fill="currentColor" viewBox="0 0 20 20">
                                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                        </svg>
                                        At least 6 characters
                                    </li>
                                    <li className={`flex items-center ${newPassword === confirmPassword && newPassword ? 'text-green-400' : ''}`}>
                                        <svg className={`w-4 h-4 mr-2 ${newPassword === confirmPassword && newPassword ? 'text-green-400' : 'text-white/20'}`} fill="currentColor" viewBox="0 0 20 20">
                                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                        </svg>
                                        Passwords match
                                    </li>
                                </ul>
                            </div>

                            {/* Reset Password Button */}
                            <button
                                onClick={handleResetPassword}
                                disabled={loading || !newPassword || !confirmPassword || newPassword !== confirmPassword}
                                className={`w-full py-4 px-6 rounded-xl font-medium text-white transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] ${
                                    loading || !newPassword || !confirmPassword || newPassword !== confirmPassword
                                        ? 'bg-gray-500 cursor-not-allowed' 
                                        : 'bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600 shadow-lg hover:shadow-green-500/25'
                                }`}
                            >
                                {loading ? (
                                    <span className="flex items-center justify-center">
                                        <svg className="animate-spin h-5 w-5 mr-3" viewBox="0 0 24 24">
                                            <circle 
                                                className="opacity-25" 
                                                cx="12" 
                                                cy="12" 
                                                r="10" 
                                                stroke="currentColor" 
                                                strokeWidth="4"
                                                fill="none"
                                            />
                                            <path 
                                                className="opacity-75" 
                                                fill="currentColor" 
                                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                            />
                                        </svg>
                                        Resetting Password...
                                    </span>
                                ) : (
                                    'Reset Password'
                                )}
                            </button>
                        </div>
                    )}

                    {/* Sign In Link */}
                    <div className="text-center mt-8">
                        <span className="text-white/60 text-sm">
                            Remember your password?{' '}
                        </span>
                        <button
                            onClick={() => router.push("/Login")}
                            className="text-sm text-cyan-300 hover:text-cyan-200 transition-colors duration-300 font-medium hover:underline"
                        >
                            Sign in
                        </button>
                    </div>
                </div>
            </div>
            <ToastContainer 
                position="top-right"
                autoClose={3000}
                hideProgressBar={false}
                newestOnTop={false}
                closeOnClick
                rtl={false}
                pauseOnFocusLoss
                draggable
                pauseOnHover
                theme="dark"
            />
        </div>
    );
}