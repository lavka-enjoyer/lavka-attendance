/**
 * Analytics dashboard component for admin panel.
 * Shows activity charts and statistics.
 */
import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
    BarChart3, TrendingUp, Users, Activity, Calendar,
    RefreshCw, Loader2, AlertTriangle
} from 'lucide-react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    LineChart, Line, PieChart, Pie, Cell
} from 'recharts';
import { SkeletonChart, SkeletonStatsCard } from '../ui/skeleton';

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];

/**
 * Stat card component.
 */
const StatCard = ({ icon: Icon, label, value, change, loading }) => (
    <div className="p-4 rounded-xl glass border border-white/10">
        <div className="flex items-center justify-between">
            <div className="p-2 rounded-lg bg-[var(--button-color)]/20 text-[var(--button-color)]">
                <Icon size={20} />
            </div>
            {change !== undefined && (
                <span className={`text-xs font-medium px-2 py-1 rounded-full ${
                    change >= 0 ? 'bg-green-500/20 text-green-500' : 'bg-red-500/20 text-red-500'
                }`}>
                    {change >= 0 ? '+' : ''}{change}%
                </span>
            )}
        </div>
        <div className="mt-3">
            <div className="text-[var(--hint-color)] text-sm">{label}</div>
            <div className="text-[var(--text-color)] text-2xl font-bold">
                {loading ? <Loader2 className="animate-spin" size={24} /> : value}
            </div>
        </div>
    </div>
);

/**
 * Custom tooltip for charts.
 */
const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
        return (
            <div className="p-3 rounded-lg glass border border-white/10 shadow-lg">
                <p className="text-[var(--text-color)] font-medium">{label}</p>
                {payload.map((entry, index) => (
                    <p key={index} className="text-sm" style={{ color: entry.color }}>
                        {entry.name}: {entry.value}
                    </p>
                ))}
            </div>
        );
    }
    return null;
};

/**
 * Main analytics dashboard component.
 */
const AnalyticsDashboard = ({ initData }) => {
    const [analytics, setAnalytics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [period, setPeriod] = useState('week');

    const fetchAnalytics = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await fetch(
                `/api/admin/analytics/dashboard?initData=${encodeURIComponent(initData)}&period=${period}`
            );
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Ошибка загрузки аналитики');
            }
            const data = await response.json();
            setAnalytics(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAnalytics();
    }, [initData, period]);

    // Transform data for charts
    const activityData = analytics?.activity_by_day || [];
    const groupData = analytics?.top_groups || [];
    const userTypeData = [
        { name: 'С логином', value: analytics?.users_with_login || 0 },
        { name: 'Без логина', value: (analytics?.total_users || 0) - (analytics?.users_with_login || 0) }
    ];

    if (error) {
        return (
            <div className="p-6 rounded-xl glass border border-red-500/20 text-center">
                <AlertTriangle size={48} className="mx-auto mb-4 text-red-500" />
                <p className="text-[var(--text-color)] font-medium mb-2">Ошибка загрузки</p>
                <p className="text-[var(--hint-color)] text-sm mb-4">{error}</p>
                <button
                    onClick={fetchAnalytics}
                    className="px-4 py-2 rounded-lg bg-[var(--button-color)] text-white"
                >
                    Повторить
                </button>
            </div>
        );
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
        >
            {/* Header with refresh */}
            <div className="flex items-center justify-between">
                <h3 className="text-[var(--text-color)] font-bold flex items-center">
                    <BarChart3 size={20} className="mr-2 text-[var(--button-color)]" />
                    Аналитика
                </h3>
                <div className="flex items-center space-x-2">
                    {/* Period selector */}
                    <select
                        value={period}
                        onChange={(e) => setPeriod(e.target.value)}
                        className="p-2 rounded-lg border border-white/10 bg-black/20 text-[var(--text-color)] text-sm focus:outline-none"
                    >
                        <option value="week">Неделя</option>
                        <option value="month">Месяц</option>
                        <option value="year">Год</option>
                    </select>
                    <button
                        onClick={fetchAnalytics}
                        disabled={loading}
                        className="p-2 rounded-lg bg-white/10 text-[var(--hint-color)] hover:bg-white/20 hover:text-[var(--text-color)] transition-colors"
                    >
                        <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
                    </button>
                </div>
            </div>

            {/* Stats cards */}
            {loading ? (
                <div className="grid grid-cols-2 gap-3">
                    {[...Array(4)].map((_, i) => (
                        <SkeletonStatsCard key={i} />
                    ))}
                </div>
            ) : (
                <div className="grid grid-cols-2 gap-3">
                    <StatCard
                        icon={Users}
                        label="Всего пользователей"
                        value={analytics?.total_users || 0}
                        loading={loading}
                    />
                    <StatCard
                        icon={Activity}
                        label="Активных за период"
                        value={analytics?.active_users || 0}
                        change={analytics?.active_users_change}
                        loading={loading}
                    />
                    <StatCard
                        icon={TrendingUp}
                        label="Новых регистраций"
                        value={analytics?.new_users || 0}
                        change={analytics?.new_users_change}
                        loading={loading}
                    />
                    <StatCard
                        icon={Calendar}
                        label="Отметок за период"
                        value={analytics?.total_markings || 0}
                        loading={loading}
                    />
                </div>
            )}

            {/* Activity chart */}
            <div className="p-4 rounded-xl glass border border-white/10">
                <h4 className="text-[var(--text-color)] font-medium mb-4">Активность по дням</h4>
                {loading ? (
                    <SkeletonChart />
                ) : activityData.length > 0 ? (
                    <ResponsiveContainer width="100%" height={200}>
                        <BarChart data={activityData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                            <XAxis
                                dataKey="date"
                                stroke="var(--hint-color)"
                                fontSize={12}
                                tickFormatter={(value) => {
                                    const date = new Date(value);
                                    return `${date.getDate()}.${date.getMonth() + 1}`;
                                }}
                            />
                            <YAxis stroke="var(--hint-color)" fontSize={12} />
                            <Tooltip content={<CustomTooltip />} />
                            <Bar dataKey="markings" name="Отметки" fill="var(--button-color)" radius={[4, 4, 0, 0]} />
                            <Bar dataKey="logins" name="Входы" fill="#10B981" radius={[4, 4, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                ) : (
                    <div className="h-[200px] flex items-center justify-center text-[var(--hint-color)]">
                        Нет данных за выбранный период
                    </div>
                )}
            </div>

            {/* Two column layout */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Top groups */}
                <div className="p-4 rounded-xl glass border border-white/10">
                    <h4 className="text-[var(--text-color)] font-medium mb-4">Топ групп по активности</h4>
                    {loading ? (
                        <div className="space-y-2">
                            {[...Array(5)].map((_, i) => (
                                <div key={i} className="h-8 animate-pulse bg-gray-200 rounded" />
                            ))}
                        </div>
                    ) : groupData.length > 0 ? (
                        <div className="space-y-2">
                            {groupData.slice(0, 5).map((group, index) => (
                                <div key={group.name} className="flex items-center justify-between p-2 rounded-lg bg-white/5">
                                    <div className="flex items-center">
                                        <span className="w-6 h-6 flex items-center justify-center rounded-full bg-[var(--button-color)]/20 text-[var(--button-color)] text-xs font-bold mr-2">
                                            {index + 1}
                                        </span>
                                        <span className="text-[var(--text-color)] text-sm">{group.name}</span>
                                    </div>
                                    <span className="text-[var(--hint-color)] text-sm">{group.count} отметок</span>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="text-center text-[var(--hint-color)] py-4">Нет данных</div>
                    )}
                </div>

                {/* User distribution pie */}
                <div className="p-4 rounded-xl glass border border-white/10">
                    <h4 className="text-[var(--text-color)] font-medium mb-4">Распределение пользователей</h4>
                    {loading ? (
                        <div className="h-[200px] flex items-center justify-center">
                            <Loader2 className="animate-spin text-[var(--button-color)]" size={32} />
                        </div>
                    ) : (
                        <ResponsiveContainer width="100%" height={200}>
                            <PieChart>
                                <Pie
                                    data={userTypeData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={50}
                                    outerRadius={80}
                                    paddingAngle={5}
                                    dataKey="value"
                                >
                                    {userTypeData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip content={<CustomTooltip />} />
                            </PieChart>
                        </ResponsiveContainer>
                    )}
                    <div className="flex justify-center space-x-4 mt-2">
                        {userTypeData.map((entry, index) => (
                            <div key={entry.name} className="flex items-center text-sm">
                                <div
                                    className="w-3 h-3 rounded-full mr-2"
                                    style={{ backgroundColor: COLORS[index % COLORS.length] }}
                                />
                                <span className="text-[var(--hint-color)]">{entry.name}: {entry.value}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Trends */}
            {analytics?.trends && analytics.trends.length > 0 && (
                <div className="p-4 rounded-xl glass border border-white/10">
                    <h4 className="text-[var(--text-color)] font-medium mb-4">Тренды</h4>
                    <ResponsiveContainer width="100%" height={200}>
                        <LineChart data={analytics.trends}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                            <XAxis dataKey="date" stroke="var(--hint-color)" fontSize={12} />
                            <YAxis stroke="var(--hint-color)" fontSize={12} />
                            <Tooltip content={<CustomTooltip />} />
                            <Line
                                type="monotone"
                                dataKey="value"
                                name="Активность"
                                stroke="var(--button-color)"
                                strokeWidth={2}
                                dot={{ fill: 'var(--button-color)', r: 4 }}
                            />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            )}
        </motion.div>
    );
};

export default AnalyticsDashboard;
