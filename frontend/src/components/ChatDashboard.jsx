import React, { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    Send, RotateCcw, Bug, ArrowLeft, Copy,
    AlertTriangle, Shield, MessageSquare, Zap, Plus,
    Trash2, History, CheckCircle, CreditCard, Phone, Mail, Link2, Building2
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useNavigate } from "react-router-dom";

// ============ LOCALSTORAGE HELPERS ============
const STORAGE_KEY = 'sticky-net-conversations';
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const loadConversations = () => {
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        return stored ? JSON.parse(stored) : [];
    } catch (e) {
        console.error('Failed to load conversations:', e);
        return [];
    }
};

const saveConversations = (conversations) => {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
    } catch (e) {
        console.error('Failed to save conversations:', e);
    }
};

const generateId = () => `conv-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

// ============ SAMPLE CONVERSATIONS FOR DEMO ============
const sampleConversations = [
    {
        id: 'sample-1',
        title: "KYC Fraud Attempt",
        preview: "Your account will be blocked...",
        isSample: true,
        createdAt: new Date().toISOString(),
        messages: [
            { sender: "scammer", text: "Dear Customer, Your SBI account will be blocked within 24 hours due to incomplete KYC. Update now: bit.ly/sbi-kyc-update", timestamp: "10:31 AM" },
            { sender: "agent", text: "oh no sir! my pension comes in this account only. i am old lady living alone. what should i do? please help me beta", timestamp: "10:32 AM" },
            { sender: "scammer", text: "Madam don't worry. Just click link and update Aadhaar. Or pay Rs.10 to UPI: sbi.kyc.update@ybl for verification", timestamp: "10:33 AM" },
            { sender: "agent", text: "beta my eyes are weak i cannot see small letters on phone. can you tell me step by step? what is this UPI you mentioned?", timestamp: "10:35 AM" },
        ],
        extractedIntel: {
            upiIds: ["sbi.kyc.update@ybl"],
            phishingLinks: ["bit.ly/sbi-kyc-update"],
            bankAccounts: [],
            phoneNumbers: [],
        },
        metrics: {
            scamDetected: true,
            confidence: 0.97,
            messagesExchanged: 4,
        }
    },
    {
        id: 'sample-2',
        title: "Lottery Scam",
        preview: "Congratulations! You won ₹50 Lakhs...",
        isSample: true,
        createdAt: new Date().toISOString(),
        messages: [
            { sender: "scammer", text: "CONGRATULATIONS! You have won ₹50,00,000 in Jio Lucky Draw! Call now: 9876543210 or send ₹500 processing fee to claim.", timestamp: "2:15 PM" },
            { sender: "agent", text: "arre wah! main toh itna lucky hun! but beta mujhe vishwas nahi ho raha. kaise pata chalega yeh sach hai?", timestamp: "2:17 PM" },
            { sender: "scammer", text: "Sir this is 100% real. I am Rajesh from Jio head office Mumbai. Send fee to PhonePe: jio.winner2024@axl and get prize in 24 hours!", timestamp: "2:19 PM" },
            { sender: "agent", text: "achha achha. beta mera nephew bhi Jio mein kaam karta hai. uska naam Suresh hai. aap jaante ho usko?", timestamp: "2:22 PM" },
            { sender: "scammer", text: "Sir Jio is very big company, 50000 employees. Please send fee fast, offer expires today only!", timestamp: "2:25 PM" },
        ],
        extractedIntel: {
            upiIds: ["jio.winner2024@axl"],
            phishingLinks: [],
            bankAccounts: [],
            phoneNumbers: ["9876543210"],
        },
        metrics: {
            scamDetected: true,
            confidence: 0.99,
            messagesExchanged: 5,
        }
    },
    {
        id: 'sample-3',
        title: "Tech Support Scam",
        preview: "Your computer has virus...",
        isSample: true,
        createdAt: new Date().toISOString(),
        messages: [
            { sender: "scammer", text: "ALERT: Your computer has been infected with dangerous virus! Call Microsoft Support immediately: 1800-XXX-XXXX. Your bank details may be compromised!", timestamp: "11:00 AM" },
            { sender: "agent", text: "oh my god! virus! but sir main toh sirf whatsapp use karti hun phone pe. mere paas computer nahi hai", timestamp: "11:02 AM" },
            { sender: "scammer", text: "Madam phone virus is even more dangerous! We need to secure your phone. Download this app: malware-link.com/secure-app", timestamp: "11:04 AM" },
            { sender: "agent", text: "app kaise download karte hain? mera beta karta hai sab. abhi woh office mein hai. raat ko aayega", timestamp: "11:07 AM" },
        ],
        extractedIntel: {
            upiIds: [],
            phishingLinks: ["malware-link.com/secure-app"],
            bankAccounts: [],
            phoneNumbers: [],
        },
        metrics: {
            scamDetected: true,
            confidence: 0.94,
            messagesExchanged: 4,
        }
    }
];

// ============ SPIDER WEB BACKGROUND ============
const WebPattern = () => (
    <div className="fixed inset-0 overflow-hidden pointer-events-none opacity-20">
        <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice">
            {Array.from({ length: 12 }).map((_, i) => {
                const angle = (i / 12) * 2 * Math.PI;
                return (
                    <line
                        key={`spoke-${i}`}
                        x1="50"
                        y1="50"
                        x2={50 + Math.cos(angle) * 50}
                        y2={50 + Math.sin(angle) * 50}
                        stroke="#00F5D4"
                        strokeWidth="0.15"
                        opacity="0.3"
                    />
                );
            })}
            {[1, 2, 3, 4, 5].map((ring) => (
                <circle
                    key={`ring-${ring}`}
                    cx="50"
                    cy="50"
                    r={ring * 10}
                    fill="none"
                    stroke="#00F5D4"
                    strokeWidth="0.1"
                    opacity="0.2"
                />
            ))}
        </svg>
    </div>
);

// ============ GLASS CONTAINER ============
const GlassPanel = ({ children, className = "", glowOnHover = true }) => (
    <div
        className={`
      glass-panel rounded-2xl border border-white/10 
      ${glowOnHover ? 'hover:border-cyber-cyan/30 hover:shadow-cyan-glow' : ''}
      transition-all duration-300
      ${className}
    `}
    >
        {children}
    </div>
);

// ============ CHAT MESSAGE ============
const ChatMessage = React.memo(({ message, isAgent }) => (
    <div className={`flex ${isAgent ? 'justify-end' : 'justify-start'} mb-4`}>
        <div
            className={`
        max-w-[80%] px-4 py-3 rounded-2xl font-mono text-sm
        ${isAgent
                    ? 'bg-cyber-cyan/20 border border-cyber-cyan/30 text-cyber-cyan ml-auto rounded-br-sm'
                    : 'bg-white/5 border border-white/10 text-gray-200 rounded-bl-sm'
                }
      `}
        >
            <p className="leading-relaxed whitespace-pre-wrap">{message.text}</p>
        </div>
    </div>
));

// ============ METRIC CARD ============
const MetricCard = React.memo(({ label, value, icon: Icon, color = "cyan" }) => {
    const colorClasses = {
        cyan: "text-cyber-cyan border-cyber-cyan/30",
        red: "text-cyber-red border-cyber-red/30",
        green: "text-green-400 border-green-400/30",
        yellow: "text-yellow-400 border-yellow-400/30",
    };

    return (
        <div className={`flex items-center justify-between py-3 border-b border-white/5 last:border-0`}>
            <div className="flex items-center gap-2">
                {Icon && <Icon className={`w-4 h-4 ${colorClasses[color]?.split(' ')[0]}`} />}
                <span className="text-gray-400 text-sm">{label}</span>
            </div>
            <span className={`font-mono font-bold ${colorClasses[color]?.split(' ')[0]}`}>
                {value}
            </span>
        </div>
    );
});

// ============ INTEL TAG ============
const IntelTag = React.memo(({ type, value }) => {
    const typeConfig = {
        upi: { 
            icon: CreditCard, 
            label: "UPI ID",
            color: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30" 
        },
        link: { 
            icon: Link2, 
            label: "Link",
            color: "bg-red-500/20 text-red-400 border-red-500/30" 
        },
        phone: { 
            icon: Phone, 
            label: "Phone",
            color: "bg-purple-500/20 text-purple-400 border-purple-500/30" 
        },
        bank: { 
            icon: Building2, 
            label: "Bank A/C",
            color: "bg-blue-500/20 text-blue-400 border-blue-500/30" 
        },
        email: { 
            icon: Mail, 
            label: "Email",
            color: "bg-green-500/20 text-green-400 border-green-500/30" 
        },
        name: { 
            icon: Building2, 
            label: "Name",
            color: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30" 
        },
        ifsc: { 
            icon: Building2, 
            label: "IFSC",
            color: "bg-indigo-500/20 text-indigo-400 border-indigo-500/30" 
        },
        whatsapp: { 
            icon: Phone, 
            label: "WhatsApp",
            color: "bg-pink-500/20 text-pink-400 border-pink-500/30" 
        },
    };

    const config = typeConfig[type] || typeConfig.upi;
    const IconComponent = config.icon;

    const handleCopy = () => {
        navigator.clipboard.writeText(value);
    };

    return (
        <div
            className={`
        flex items-center gap-2 px-3 py-2 rounded-lg border font-mono text-xs
        ${config.color}
      `}
        >
            <IconComponent className="w-4 h-4 flex-shrink-0" />
            <span className="font-semibold flex-shrink-0">{config.label}:</span>
            <span className="truncate flex-1">{value}</span>
            <button onClick={handleCopy} className="ml-auto hover:opacity-70 transition-opacity flex-shrink-0">
                <Copy className="w-3 h-3" />
            </button>
        </div>
    );
});

// ============ CONVERSATION CARD ============
const ConversationCard = React.memo(({ conversation, onClick, isActive, onDelete }) => (
    <div
        className={`
      w-full text-left p-4 rounded-xl border transition-all duration-300 relative group
      ${isActive
                ? 'bg-cyber-cyan/10 border-cyber-cyan/50 shadow-cyan-glow'
                : 'bg-white/5 border-white/10 hover:border-white/20'
            }
    `}
    >
        <button onClick={onClick} className="w-full text-left">
            <div className="flex items-center gap-2 mb-2">
                {conversation.isSample ? (
                    <Zap className="w-4 h-4 text-yellow-400" />
                ) : (
                    <History className="w-4 h-4 text-cyber-cyan" />
                )}
                <span className="font-semibold text-white text-sm truncate flex-1">
                    {conversation.title}
                </span>
            </div>
            <p className="text-gray-500 text-xs font-mono truncate">{conversation.preview}</p>
            <div className="flex items-center gap-3 mt-2">
                {conversation.metrics?.confidence && (
                    <span className="text-[10px] text-cyber-cyan font-mono">
                        {(conversation.metrics.confidence * 100).toFixed(0)}% conf
                    </span>
                )}
                <span className="text-[10px] text-gray-500">
                    {conversation.messages?.length || 0} msgs
                </span>
            </div>
        </button>
        {!conversation.isSample && onDelete && (
            <button
                onClick={(e) => { e.stopPropagation(); onDelete(conversation.id); }}
                className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-red-500/20 rounded"
            >
                <Trash2 className="w-3 h-3 text-red-400" />
            </button>
        )}
    </div>
));

// ============ MAIN CHAT DASHBOARD ============
const ChatDashboard = () => {
    const navigate = useNavigate();
    const [savedConversations, setSavedConversations] = useState([]);
    const [currentConversationId, setCurrentConversationId] = useState(null);
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [channel, setChannel] = useState("SMS");
    const [locale, setLocale] = useState("IN");
    const [metrics, setMetrics] = useState({
        scamDetected: null,
        confidence: null,
        messagesExchanged: 0,
    });
    const [extractedIntel, setExtractedIntel] = useState({
        upiIds: [],
        phishingLinks: [],
        bankAccounts: [],
        phoneNumbers: [],
        emails: [],
        beneficiaryNames: [],
        ifscCodes: [],
        whatsappNumbers: [],
    });
    const [agentNotes, setAgentNotes] = useState("");
    const [connectionStatus, setConnectionStatus] = useState('unknown'); // 'connected', 'disconnected', 'unknown'

    const messagesEndRef = useRef(null);
    const messagesContainerRef = useRef(null);
    const inputRef = useRef(null);

    // Load saved conversations on mount
    useEffect(() => {
        const loaded = loadConversations();
        setSavedConversations(loaded);
    }, []);

    // Auto-scroll to bottom when new messages arrive
    useEffect(() => {
        if (messages.length > 0 && messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: "auto" });
        }
    }, [messages.length]);

    // Save current conversation to localStorage whenever it changes
    const saveCurrentConversation = useCallback(() => {
        if (!currentConversationId || messages.length === 0) return;

        const conversationData = {
            id: currentConversationId,
            title: messages[0]?.text?.substring(0, 40) + '...' || 'New Conversation',
            preview: messages[0]?.text?.substring(0, 50) || '',
            createdAt: new Date().toISOString(),
            messages,
            extractedIntel,
            metrics,
            agentNotes,
        };

        setSavedConversations(prev => {
            const existing = prev.findIndex(c => c.id === currentConversationId);
            let updated;
            if (existing >= 0) {
                updated = [...prev];
                updated[existing] = conversationData;
            } else {
                updated = [conversationData, ...prev];
            }
            saveConversations(updated);
            return updated;
        });
    }, [currentConversationId, messages, extractedIntel, metrics, agentNotes]);

    // Auto-save when messages change
    useEffect(() => {
        if (messages.length > 0 && currentConversationId) {
            saveCurrentConversation();
        }
    }, [messages, saveCurrentConversation, currentConversationId]);

    // Check backend connection
    useEffect(() => {
        const checkConnection = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/health`, { method: 'GET' });
                setConnectionStatus(response.ok ? 'connected' : 'disconnected');
            } catch {
                setConnectionStatus('disconnected');
            }
        };
        checkConnection();
    }, []);

    const handleSelectConversation = (conversation) => {
        // For sample conversations, create a read-only view (new ID to prevent saving)
        const isReadOnly = conversation.isSample;
        setCurrentConversationId(isReadOnly ? null : conversation.id);
        setMessages(conversation.messages || []);
        setMetrics(conversation.metrics || {
            scamDetected: null,
            confidence: null,
            messagesExchanged: conversation.messages?.length || 0,
        });
        setExtractedIntel(conversation.extractedIntel || {
            upiIds: [],
            phishingLinks: [],
            bankAccounts: [],
            phoneNumbers: [],
            emails: [],
        });
        setAgentNotes(conversation.agentNotes || "");
    };

    const handleDeleteConversation = (id) => {
        setSavedConversations(prev => {
            const updated = prev.filter(c => c.id !== id);
            saveConversations(updated);
            return updated;
        });
        if (currentConversationId === id) {
            handleNewConversation();
        }
    };

    const handleNewConversation = () => {
        const newId = generateId();
        setCurrentConversationId(newId);
        setMessages([]);
        setMetrics({
            scamDetected: null,
            confidence: null,
            messagesExchanged: 0,
        });
        setExtractedIntel({
            upiIds: [],
            phishingLinks: [],
            bankAccounts: [],
            phoneNumbers: [],
            emails: [],
        });
        setAgentNotes("");
        inputRef.current?.focus();
    };

    const handleSend = async () => {
        if (!inputValue.trim() || isLoading) return;

        // If viewing a sample, create a new conversation first
        const activeConversation = allConversations.find(c => c.id === currentConversationId);
        if (activeConversation?.isSample || !currentConversationId) {
            const newId = generateId();
            setCurrentConversationId(newId);
            setMessages([]);
            setMetrics({
                scamDetected: null,
                confidence: null,
                messagesExchanged: 0,
            });
            setExtractedIntel({
                upiIds: [],
                phishingLinks: [],
                bankAccounts: [],
                phoneNumbers: [],
                emails: [],
            });
            setAgentNotes("");
        }

        const timestamp = new Date().toISOString();
        const displayTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        const newMessage = {
            sender: "scammer",
            text: inputValue.trim(),
            timestamp: displayTime,
            isoTimestamp: timestamp,
        };

        setMessages(prev => [...prev, newMessage]);
        setInputValue("");
        setIsLoading(true);

        try {
            // Build conversation history for API
            const conversationHistory = messages.map(m => ({
                sender: m.sender,
                text: m.text,
                timestamp: m.isoTimestamp || new Date().toISOString(),
            }));

            const response = await fetch(`${API_BASE_URL}/api/v1/analyze`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: {
                        sender: "scammer",
                        text: newMessage.text,
                        timestamp: timestamp,
                    },
                    conversationHistory,
                    metadata: {
                        channel,
                        language: "English",
                        locale,
                    }
                }),
            });

            if (!response.ok) {
                throw new Error(`API returned ${response.status}`);
            }

            const data = await response.json();
            setConnectionStatus('connected');

            if (data.status === "success") {
                // Add agent response
                if (data.agentResponse) {
                    const agentTimestamp = new Date().toISOString();
                    setMessages(prev => [...prev, {
                        sender: "agent",
                        text: data.agentResponse,
                        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                        isoTimestamp: agentTimestamp,
                    }]);
                }

                // Update metrics
                setMetrics(prev => ({
                    scamDetected: data.scamDetected,
                    confidence: data.confidence || prev.confidence,
                    messagesExchanged: prev.messagesExchanged + (data.agentResponse ? 2 : 1),
                }));

                // Update intel from response
                if (data.extractedIntelligence) {
                    const intel = data.extractedIntelligence;
                    setExtractedIntel(prev => ({
                        upiIds: [...new Set([...prev.upiIds, ...(intel.upiIds || [])])],
                        phishingLinks: [...new Set([...prev.phishingLinks, ...(intel.phishingLinks || [])])],
                        bankAccounts: [...new Set([...prev.bankAccounts, ...(intel.bankAccounts || [])])],
                        phoneNumbers: [...new Set([...prev.phoneNumbers, ...(intel.phoneNumbers || [])])],
                        emails: [...new Set([...(prev.emails || []), ...(intel.emails || [])])],
                        beneficiaryNames: [...new Set([...(prev.beneficiaryNames || []), ...(intel.beneficiaryNames || [])])],
                        ifscCodes: [...new Set([...(prev.ifscCodes || []), ...(intel.ifscCodes || [])])],
                        whatsappNumbers: [...new Set([...(prev.whatsappNumbers || []), ...(intel.whatsappNumbers || [])])],
                    }));
                }

                if (data.agentNotes) {
                    setAgentNotes(data.agentNotes);
                }
            }
        } catch (error) {
            console.error("API Error:", error);
            setConnectionStatus('disconnected');

            // Show error in agent notes
            setAgentNotes(`Connection error: ${error.message}. Make sure the backend is running at ${API_BASE_URL}`);
        }

        setIsLoading(false);
    };

    const handleReset = () => {
        handleNewConversation();
    };

    const hasIntel = extractedIntel.upiIds.length > 0 ||
        extractedIntel.phishingLinks.length > 0 ||
        extractedIntel.bankAccounts.length > 0 ||
        extractedIntel.phoneNumbers?.length > 0 ||
        extractedIntel.emails?.length > 0 ||
        extractedIntel.beneficiaryNames?.length > 0 ||
        extractedIntel.ifscCodes?.length > 0 ||
        extractedIntel.whatsappNumbers?.length > 0;

    // Combine samples and saved conversations
    const allConversations = [...sampleConversations, ...savedConversations];
    
    // Check if viewing a sample conversation
    const isViewingSample = !currentConversationId && messages.length > 0;

    return (
        <div className="h-screen bg-obsidian relative overflow-hidden flex flex-col">
            <WebPattern />

            {/* Header */}
            <header className="fixed top-0 left-0 right-0 z-50 glass-panel border-b border-white/10">
                <div className="max-w-[1800px] mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => navigate('/')}
                            className="text-gray-400 hover:text-white"
                        >
                            <ArrowLeft className="w-4 h-4 mr-2" />
                            Back
                        </Button>
                        <div className="h-6 w-px bg-white/10" />
                        <div className="flex items-center gap-2">
                            <Bug className="w-6 h-6 text-cyber-cyan" />
                            <span className="font-heading font-bold text-xl text-white">Sticky-Net</span>
                        </div>
                    </div>
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2">
                            <div className={`w-2 h-2 rounded-full ${connectionStatus === 'connected' ? 'bg-green-400' :
                                    connectionStatus === 'disconnected' ? 'bg-red-400' : 'bg-yellow-400'
                                }`} />
                            <span className="text-xs text-gray-400 font-mono">
                                {connectionStatus === 'connected' ? 'API Connected' :
                                    connectionStatus === 'disconnected' ? 'API Offline' : 'Checking...'}
                            </span>
                        </div>
                        <Badge className="border-cyber-cyan text-cyber-cyan bg-cyber-cyan/10 font-mono">
                            CONVERSATION TESTER
                        </Badge>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="flex-1 pt-20 px-4 md:px-6 pb-4 overflow-hidden">
                <div className="max-w-[1800px] mx-auto h-full grid grid-cols-12 gap-4 md:gap-6">

                    {/* Conversations Sidebar */}
                    <div className="col-span-12 lg:col-span-2 h-full min-h-0">
                        <GlassPanel className="h-full p-4 flex flex-col min-h-0">
                            <div className="flex items-center justify-between mb-4 flex-shrink-0">
                                <h3 className="text-white font-semibold flex items-center gap-2">
                                    <History className="w-4 h-4 text-cyber-cyan" />
                                    Conversations
                                </h3>
                                <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={handleNewConversation}
                                    className="h-8 w-8 p-0 text-cyber-cyan hover:bg-cyber-cyan/10"
                                >
                                    <Plus className="w-4 h-4" />
                                </Button>
                            </div>

                            <div className="flex-1 min-h-0 overflow-y-auto pr-1" style={{ scrollbarWidth: 'thin' }}>
                                <div className="space-y-3">
                                    {/* Sample Conversations */}
                                    <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">Examples</div>
                                {sampleConversations.map((conv) => (
                                    <ConversationCard
                                        key={conv.id}
                                        conversation={conv}
                                        isActive={currentConversationId === conv.id}
                                        onClick={() => handleSelectConversation(conv)}
                                    />
                                ))}

                                {/* Saved Conversations */}
                                {savedConversations.length > 0 && (
                                    <>
                                        <div className="text-xs text-gray-500 uppercase tracking-wider mt-4 mb-2">Your Chats</div>
                                        {savedConversations.map((conv) => (
                                            <ConversationCard
                                                key={conv.id}
                                                conversation={conv}
                                                isActive={currentConversationId === conv.id}
                                                onClick={() => handleSelectConversation(conv)}
                                                onDelete={handleDeleteConversation}
                                            />
                                        ))}
                                    </>
                                )}
                                </div>
                            </div>
                        </GlassPanel>
                    </div>

                    {/* Chat Window */}
                    <div className="col-span-12 lg:col-span-6 h-full min-h-0">
                        <GlassPanel className="h-full flex flex-col min-h-0">
                            {/* Chat Header */}
                            <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between flex-shrink-0">
                                <div className="flex items-center gap-3">
                                    <div className={`w-3 h-3 rounded-full ${isLoading ? 'bg-yellow-400 animate-pulse' : 'bg-cyber-cyan'}`} />
                                    <h2 className="text-white font-semibold">Conversation</h2>
                                    <Badge variant="outline" className="text-gray-400 border-gray-600 text-xs">
                                        {isLoading ? 'PROCESSING' : 'MONITORING'}
                                    </Badge>
                                    {!currentConversationId && messages.length > 0 && (
                                        <Badge variant="outline" className="text-yellow-400 border-yellow-400/30 bg-yellow-400/5 text-xs">
                                            DEMO - READ ONLY
                                        </Badge>
                                    )}
                                </div>
                                <Button
                                    size="sm"
                                    variant="destructive"
                                    onClick={handleReset}
                                    className="bg-cyber-red/20 text-cyber-red border border-cyber-red/30 hover:bg-cyber-red/30"
                                >
                                    <RotateCcw className="w-4 h-4 mr-2" />
                                    Reset
                                </Button>
                            </div>

                            {/* Messages Area */}
                            <div 
                                ref={messagesContainerRef}
                                className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden p-4 md:p-6"
                                style={{ scrollbarWidth: 'thin' }}
                            >
                                {messages.length === 0 ? (
                                    <div className="h-full flex flex-col items-center justify-center text-gray-500">
                                        <MessageSquare className="w-16 h-16 mb-4 opacity-30" />
                                        <p className="text-center font-mono text-sm">
                                            Start a conversation by typing a scam message below.
                                        </p>
                                        <p className="text-center text-xs mt-2 text-gray-600">
                                            Example: "Your bank account has been compromised. Send OTP to verify."
                                        </p>
                                        {connectionStatus === 'disconnected' && (
                                            <p className="text-center text-xs mt-4 text-red-400">
                                                ⚠️ Backend not connected. Start the server at {API_BASE_URL}
                                            </p>
                                        )}
                                    </div>
                                ) : (
                                    <>
                                        {messages.map((msg, idx) => (
                                            <ChatMessage
                                                key={`msg-${idx}`}
                                                message={msg}
                                                isAgent={msg.sender === "agent"}
                                            />
                                        ))}
                                    </>
                                )}
                                {isLoading && (
                                    <div className="flex justify-end mb-4">
                                        <div className="bg-cyber-cyan/20 border border-cyber-cyan/30 rounded-2xl rounded-br-sm px-4 py-3">
                                            <div className="flex gap-1">
                                                <span className="w-2 h-2 bg-cyber-cyan rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                                <span className="w-2 h-2 bg-cyber-cyan rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                                <span className="w-2 h-2 bg-cyber-cyan rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                            </div>
                                        </div>
                                    </div>
                                )}
                                <div ref={messagesEndRef} />
                            </div>

                            {/* Input Area */}
                            <div className="p-4 border-t border-white/10 flex-shrink-0">
                                {isViewingSample ? (
                                    <div className="text-center py-4">
                                        <p className="text-gray-500 text-sm font-mono">
                                            📖 This is a demo example. Click "New" to start your own conversation.
                                        </p>
                                    </div>
                                ) : (
                                    <div className="flex gap-3 items-end">
                                        <textarea
                                            ref={inputRef}
                                            value={inputValue}
                                            onChange={(e) => setInputValue(e.target.value)}
                                            onPaste={(e) => {
                                                // Let default paste behavior work, then trigger resize
                                                setTimeout(() => {
                                                    if (inputRef.current) {
                                                        inputRef.current.style.height = 'auto';
                                                        inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 200) + 'px';
                                                    }
                                                }, 0);
                                            }}
                                            onKeyDown={(e) => {
                                                if (e.key === 'Enter' && !e.shiftKey) {
                                                    e.preventDefault();
                                                    handleSend();
                                                }
                                            }}
                                            placeholder="Type scammer message... (Shift+Enter for new line)"
                                            rows={3}
                                            className="
                      flex-1 bg-black border border-white/20 rounded-xl px-4 py-3
                      font-mono text-sm text-gray-200 placeholder:text-gray-600
                      focus:outline-none focus:border-cyber-cyan focus:shadow-cyan-glow
                      transition-all duration-300 resize-none overflow-y-auto scrollbar-thin
                      min-h-[80px] max-h-[200px]
                    "
                                            style={{
                                                height: 'auto',
                                                lineHeight: '1.5rem',
                                                whiteSpace: 'pre-wrap',
                                                wordWrap: 'break-word',
                                                overflowWrap: 'break-word'
                                            }}
                                            onInput={(e) => {
                                                e.target.style.height = 'auto';
                                                e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px';
                                            }}
                                        />
                                        <Button
                                            onClick={handleSend}
                                            disabled={isLoading || !inputValue.trim()}
                                            className="
                      bg-cyber-cyan text-black font-mono font-bold px-6
                      hover:bg-cyber-cyan/80 disabled:opacity-50
                      shadow-cyan-glow transition-all duration-300 h-[44px]
                    "
                                        >
                                            <Send className="w-4 h-4 mr-2" />
                                            Send
                                        </Button>
                                    </div>
                                )}
                            </div>
                        </GlassPanel>
                    </div>

                    {/* Right Sidebar - Metrics & Intel */}
                    <div className="col-span-12 lg:col-span-4 h-full min-h-0 flex flex-col gap-4 md:gap-6">
                        {/* Configuration */}
                        <GlassPanel className="p-5 flex-shrink-0">
                            <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
                                <Shield className="w-4 h-4 text-gray-400" />
                                Configuration
                            </h3>
                            <div className="grid grid-cols-2 gap-4 mb-4">
                                <div>
                                    <label className="text-gray-500 text-xs mb-1 block">CHANNEL</label>
                                    <select
                                        value={channel}
                                        onChange={(e) => setChannel(e.target.value)}
                                        className="w-full bg-black/50 border border-white/10 rounded-lg px-3 py-2 text-white text-sm font-mono focus:outline-none focus:border-cyber-cyan"
                                    >
                                        <option value="SMS">SMS</option>
                                        <option value="WhatsApp">WhatsApp</option>
                                        <option value="Email">Email</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="text-gray-500 text-xs mb-1 block">LOCALE</label>
                                    <select
                                        value={locale}
                                        onChange={(e) => setLocale(e.target.value)}
                                        className="w-full bg-black/50 border border-white/10 rounded-lg px-3 py-2 text-white text-sm font-mono focus:outline-none focus:border-cyber-cyan"
                                    >
                                        <option value="IN">India (IN)</option>
                                        <option value="US">USA (US)</option>
                                        <option value="UK">UK (UK)</option>
                                    </select>
                                </div>
                            </div>
                        </GlassPanel>

                        {/* Detection Metrics */}
                        <GlassPanel className="p-5 flex-shrink-0">
                            <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
                                <AlertTriangle className="w-4 h-4 text-cyber-red" />
                                Detection Metrics
                            </h3>
                            <div className="space-y-1">
                                <MetricCard
                                    label="Scam Detected"
                                    value={metrics.scamDetected === null ? "-" : metrics.scamDetected ? "YES" : "NO"}
                                    icon={metrics.scamDetected ? AlertTriangle : CheckCircle}
                                    color={metrics.scamDetected ? "red" : "green"}
                                />
                                <MetricCard
                                    label="Confidence"
                                    value={metrics.confidence !== null ? `${(metrics.confidence * 100).toFixed(0)}%` : "-"}
                                    color={metrics.confidence > 0.8 ? "red" : metrics.confidence > 0.5 ? "yellow" : "green"}
                                />
                                <div className="h-2 bg-white/5 rounded-full overflow-hidden mt-2 mb-3">
                                    <div
                                        className={`h-full transition-all duration-500 ease-out ${metrics.confidence > 0.8 ? 'bg-cyber-red' : metrics.confidence > 0.5 ? 'bg-yellow-400' : 'bg-green-400'}`}
                                        style={{ width: `${(metrics.confidence || 0) * 100}%` }}
                                    />
                                </div>
                                <MetricCard
                                    label="Messages Exchanged"
                                    value={metrics.messagesExchanged}
                                    icon={MessageSquare}
                                    color="cyan"
                                />
                            </div>
                        </GlassPanel>

                        {/* Extracted Intelligence */}
                        <GlassPanel className="p-5 flex-1 min-h-0 overflow-hidden flex flex-col">
                            <h3 className="text-white font-semibold mb-4 flex items-center gap-2 flex-shrink-0">
                                <Zap className="w-4 h-4 text-yellow-400" />
                                Extracted Intelligence
                            </h3>
                            <div className="flex-1 min-h-0 overflow-y-auto scrollbar-thin space-y-2 pr-2">
                                {!hasIntel ? (
                                    <div className="h-full flex items-center justify-center text-gray-600 text-sm font-mono">
                                        No intelligence extracted yet.
                                    </div>
                                ) : (
                                    <>
                                        {extractedIntel.upiIds.map((upi, idx) => (
                                            <IntelTag key={`upi-${idx}`} type="upi" value={upi} />
                                        ))}
                                        {extractedIntel.phishingLinks.map((link, idx) => (
                                            <IntelTag key={`link-${idx}`} type="link" value={link} />
                                        ))}
                                        {extractedIntel.bankAccounts.map((acc, idx) => (
                                            <IntelTag key={`bank-${idx}`} type="bank" value={acc} />
                                        ))}
                                        {extractedIntel.phoneNumbers?.map((phone, idx) => (
                                            <IntelTag key={`phone-${idx}`} type="phone" value={phone} />
                                        ))}
                                        {extractedIntel.emails?.map((email, idx) => (
                                            <IntelTag key={`email-${idx}`} type="email" value={email} />
                                        ))}
                                        {extractedIntel.beneficiaryNames?.map((name, idx) => (
                                            <IntelTag key={`name-${idx}`} type="name" value={name} />
                                        ))}
                                        {extractedIntel.ifscCodes?.map((ifsc, idx) => (
                                            <IntelTag key={`ifsc-${idx}`} type="ifsc" value={ifsc} />
                                        ))}
                                        {extractedIntel.whatsappNumbers?.map((wa, idx) => (
                                            <IntelTag key={`whatsapp-${idx}`} type="whatsapp" value={wa} />
                                        ))}
                                    </>
                                )}
                            </div>
                        </GlassPanel>

                        {/* Agent Notes */}
                        <GlassPanel className="p-5 flex-shrink-0">
                            <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
                                📝 Agent Notes
                            </h3>
                            <p className="text-gray-400 text-sm font-mono leading-relaxed whitespace-pre-wrap">
                                {agentNotes || "-"}
                            </p>
                        </GlassPanel>
                    </div>
                </div>
            </main>
        </div>
    );
};

export default ChatDashboard;