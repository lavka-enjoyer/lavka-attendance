/**
 * Bulk import component for admin panel.
 * Allows importing users from CSV files.
 */
import React, { useState, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Upload, FileText, CheckCircle, AlertTriangle, X,
    Loader2, Download, Eye, Users, AlertCircle
} from 'lucide-react';
import Papa from 'papaparse';
import { showSuccess, showError } from '../ui/toaster';

/**
 * CSV preview table.
 */
const PreviewTable = ({ data, headers }) => {
    if (!data || data.length === 0) return null;

    return (
        <div className="overflow-auto max-h-60 rounded-lg border border-white/10">
            <table className="w-full text-sm">
                <thead className="bg-white/10 sticky top-0">
                    <tr>
                        {headers.map((header, i) => (
                            <th key={i} className="px-3 py-2 text-left text-[var(--text-color)] font-medium">
                                {header}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {data.slice(0, 10).map((row, i) => (
                        <tr key={i} className="border-t border-white/5">
                            {headers.map((header, j) => (
                                <td key={j} className="px-3 py-2 text-[var(--hint-color)]">
                                    {row[header] || '-'}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
            {data.length > 10 && (
                <div className="p-2 text-center text-xs text-[var(--hint-color)] bg-white/5">
                    ...и ещё {data.length - 10} записей
                </div>
            )}
        </div>
    );
};

/**
 * Validation result display.
 */
const ValidationResult = ({ result }) => {
    if (!result) return null;

    return (
        <div className="space-y-2">
            <div className="flex items-center justify-between p-3 rounded-lg bg-white/5">
                <div className="flex items-center">
                    <CheckCircle size={16} className="mr-2 text-green-500" />
                    <span className="text-[var(--text-color)]">Валидных записей</span>
                </div>
                <span className="font-bold text-green-500">{result.valid}</span>
            </div>
            {result.errors > 0 && (
                <div className="flex items-center justify-between p-3 rounded-lg bg-red-500/10">
                    <div className="flex items-center">
                        <AlertCircle size={16} className="mr-2 text-red-500" />
                        <span className="text-[var(--text-color)]">С ошибками</span>
                    </div>
                    <span className="font-bold text-red-500">{result.errors}</span>
                </div>
            )}
            {result.duplicates > 0 && (
                <div className="flex items-center justify-between p-3 rounded-lg bg-yellow-500/10">
                    <div className="flex items-center">
                        <AlertTriangle size={16} className="mr-2 text-yellow-500" />
                        <span className="text-[var(--text-color)]">Дубликаты</span>
                    </div>
                    <span className="font-bold text-yellow-500">{result.duplicates}</span>
                </div>
            )}
        </div>
    );
};

/**
 * Main bulk import component.
 */
const BulkImport = ({ initData, onRefresh }) => {
    const [file, setFile] = useState(null);
    const [parsedData, setParsedData] = useState(null);
    const [headers, setHeaders] = useState([]);
    const [validation, setValidation] = useState(null);
    const [loading, setLoading] = useState(false);
    const [importing, setImporting] = useState(false);
    const [result, setResult] = useState(null);
    const fileInputRef = useRef(null);

    // Required fields
    const REQUIRED_FIELDS = ['tg_userid', 'group_name'];
    const OPTIONAL_FIELDS = ['login', 'fio', 'allowConfirm', 'admin_lvl'];

    const handleFileSelect = useCallback((e) => {
        const selectedFile = e.target.files[0];
        if (!selectedFile) return;

        if (!selectedFile.name.endsWith('.csv')) {
            showError('Пожалуйста, выберите CSV файл');
            return;
        }

        setFile(selectedFile);
        setResult(null);
        setLoading(true);

        Papa.parse(selectedFile, {
            header: true,
            skipEmptyLines: true,
            complete: (results) => {
                setParsedData(results.data);
                setHeaders(results.meta.fields || []);
                validateData(results.data, results.meta.fields || []);
                setLoading(false);
            },
            error: (error) => {
                showError(`Ошибка парсинга: ${error.message}`);
                setLoading(false);
            }
        });
    }, []);

    const validateData = (data, fields) => {
        // Check required fields
        const missingFields = REQUIRED_FIELDS.filter(f => !fields.includes(f));
        if (missingFields.length > 0) {
            setValidation({
                valid: 0,
                errors: data.length,
                duplicates: 0,
                missingFields,
                message: `Отсутствуют обязательные поля: ${missingFields.join(', ')}`
            });
            return;
        }

        // Validate rows
        let valid = 0;
        let errors = 0;
        const seenIds = new Set();
        let duplicates = 0;

        data.forEach(row => {
            const tgId = row.tg_userid;

            // Check for duplicates
            if (seenIds.has(tgId)) {
                duplicates++;
                return;
            }
            seenIds.add(tgId);

            // Validate required fields
            if (!tgId || !row.group_name) {
                errors++;
                return;
            }

            // Validate tg_userid is a number
            if (isNaN(parseInt(tgId))) {
                errors++;
                return;
            }

            valid++;
        });

        setValidation({ valid, errors, duplicates });
    };

    const handleImport = async () => {
        if (!parsedData || parsedData.length === 0 || validation?.valid === 0) {
            showError('Нет валидных данных для импорта');
            return;
        }

        setImporting(true);
        try {
            // Prepare data for import
            const usersToImport = parsedData
                .filter(row => row.tg_userid && row.group_name && !isNaN(parseInt(row.tg_userid)))
                .map(row => ({
                    tg_userid: parseInt(row.tg_userid),
                    group_name: row.group_name,
                    login: row.login || null,
                    fio: row.fio || null,
                    allowConfirm: row.allowConfirm === 'true' || row.allowConfirm === '1',
                    admin_lvl: parseInt(row.admin_lvl) || 0
                }));

            const response = await fetch('/api/admin/bulk_import', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    initData,
                    users: usersToImport
                })
            });

            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Ошибка импорта');

            setResult({
                created: data.created || [],
                updated: data.updated || [],
                failed: data.failed || [],
                errors: data.errors || {}
            });

            showSuccess(`Импортировано: ${data.created?.length || 0} новых, ${data.updated?.length || 0} обновлено`);
            onRefresh?.();
        } catch (error) {
            showError(error.message);
        } finally {
            setImporting(false);
        }
    };

    const handleReset = () => {
        setFile(null);
        setParsedData(null);
        setHeaders([]);
        setValidation(null);
        setResult(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    const downloadTemplate = () => {
        const template = [
            [...REQUIRED_FIELDS, ...OPTIONAL_FIELDS].join(','),
            '123456789,ИКБО-01-23,ivanov,Иванов Иван Иванович,true,0'
        ].join('\n');

        const blob = new Blob([template], { type: 'text/csv;charset=utf-8;' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'import_template.csv';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
        >
            {/* Header */}
            <div className="flex items-center justify-between">
                <h3 className="text-[var(--text-color)] font-bold flex items-center">
                    <Upload size={20} className="mr-2 text-[var(--button-color)]" />
                    Импорт пользователей
                </h3>
                <button
                    onClick={downloadTemplate}
                    className="flex items-center px-3 py-2 rounded-lg bg-white/10 text-[var(--hint-color)] hover:bg-white/20 hover:text-[var(--text-color)] transition-colors text-sm"
                >
                    <Download size={14} className="mr-1" />
                    Шаблон
                </button>
            </div>

            {/* Info */}
            <div className="p-4 rounded-xl bg-[var(--button-color)]/10 border border-[var(--button-color)]/20">
                <div className="flex items-start">
                    <AlertTriangle size={18} className="mr-2 mt-0.5 text-[var(--button-color)]" />
                    <div className="text-sm">
                        <p className="text-[var(--text-color)] font-medium mb-1">Формат файла</p>
                        <p className="text-[var(--hint-color)]">
                            Обязательные поля: <code className="bg-white/10 px-1 rounded">tg_userid</code>, <code className="bg-white/10 px-1 rounded">group_name</code>
                        </p>
                        <p className="text-[var(--hint-color)] mt-1">
                            Опциональные: <code className="bg-white/10 px-1 rounded">login</code>, <code className="bg-white/10 px-1 rounded">fio</code>, <code className="bg-white/10 px-1 rounded">allowConfirm</code>, <code className="bg-white/10 px-1 rounded">admin_lvl</code>
                        </p>
                    </div>
                </div>
            </div>

            {/* File upload */}
            {!file ? (
                <div
                    className="p-8 rounded-xl border-2 border-dashed border-white/20 text-center cursor-pointer hover:border-[var(--button-color)]/50 transition-colors"
                    onClick={() => fileInputRef.current?.click()}
                >
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept=".csv"
                        onChange={handleFileSelect}
                        className="hidden"
                    />
                    <FileText size={48} className="mx-auto mb-4 text-[var(--hint-color)]" />
                    <p className="text-[var(--text-color)] font-medium mb-1">Выберите CSV файл</p>
                    <p className="text-[var(--hint-color)] text-sm">или перетащите его сюда</p>
                </div>
            ) : (
                <div className="p-4 rounded-xl glass border border-white/10">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center">
                            <FileText size={20} className="mr-2 text-[var(--button-color)]" />
                            <div>
                                <span className="text-[var(--text-color)] font-medium">{file.name}</span>
                                <span className="text-[var(--hint-color)] text-sm ml-2">
                                    ({(file.size / 1024).toFixed(1)} KB)
                                </span>
                            </div>
                        </div>
                        <button
                            onClick={handleReset}
                            className="p-2 rounded-lg hover:bg-white/10 text-[var(--hint-color)]"
                        >
                            <X size={18} />
                        </button>
                    </div>

                    {loading && (
                        <div className="flex items-center justify-center p-4">
                            <Loader2 className="animate-spin mr-2 text-[var(--button-color)]" size={20} />
                            <span className="text-[var(--hint-color)]">Анализ файла...</span>
                        </div>
                    )}

                    {!loading && validation && (
                        <>
                            {/* Validation result */}
                            {validation.missingFields ? (
                                <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 mb-4">
                                    <div className="flex items-center mb-2">
                                        <AlertTriangle size={16} className="mr-2 text-red-500" />
                                        <span className="text-red-500 font-medium">Ошибка валидации</span>
                                    </div>
                                    <p className="text-[var(--hint-color)] text-sm">{validation.message}</p>
                                </div>
                            ) : (
                                <div className="mb-4">
                                    <ValidationResult result={validation} />
                                </div>
                            )}

                            {/* Preview */}
                            {parsedData && parsedData.length > 0 && (
                                <div className="mb-4">
                                    <div className="flex items-center mb-2">
                                        <Eye size={16} className="mr-2 text-[var(--hint-color)]" />
                                        <span className="text-[var(--text-color)] font-medium text-sm">Предпросмотр данных</span>
                                    </div>
                                    <PreviewTable data={parsedData} headers={headers} />
                                </div>
                            )}

                            {/* Import button */}
                            {validation.valid > 0 && !validation.missingFields && (
                                <button
                                    onClick={handleImport}
                                    disabled={importing}
                                    className="w-full py-3 px-4 rounded-xl bg-[var(--button-color)] text-white font-medium disabled:opacity-50 flex items-center justify-center"
                                >
                                    {importing ? (
                                        <>
                                            <Loader2 className="animate-spin mr-2" size={18} />
                                            Импорт...
                                        </>
                                    ) : (
                                        <>
                                            <Users size={18} className="mr-2" />
                                            Импортировать {validation.valid} пользователей
                                        </>
                                    )}
                                </button>
                            )}
                        </>
                    )}
                </div>
            )}

            {/* Import result */}
            <AnimatePresence>
                {result && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        className="p-4 rounded-xl glass border border-white/10"
                    >
                        <h4 className="text-[var(--text-color)] font-medium mb-3 flex items-center">
                            <CheckCircle size={18} className="mr-2 text-green-500" />
                            Результат импорта
                        </h4>
                        <div className="grid grid-cols-3 gap-2 text-center">
                            <div className="p-3 rounded-lg bg-green-500/10">
                                <div className="text-2xl font-bold text-green-500">{result.created.length}</div>
                                <div className="text-xs text-[var(--hint-color)]">Создано</div>
                            </div>
                            <div className="p-3 rounded-lg bg-blue-500/10">
                                <div className="text-2xl font-bold text-blue-500">{result.updated.length}</div>
                                <div className="text-xs text-[var(--hint-color)]">Обновлено</div>
                            </div>
                            <div className="p-3 rounded-lg bg-red-500/10">
                                <div className="text-2xl font-bold text-red-500">{result.failed.length}</div>
                                <div className="text-xs text-[var(--hint-color)]">Ошибок</div>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
};

export default BulkImport;
