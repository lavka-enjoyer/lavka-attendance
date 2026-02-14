import * as telegramUtils from './telegramUtils';
import { cn } from '../lib/utils';

export {
    telegramUtils,
    cn
};

// Экспорт по умолчанию объект со всеми утилитами
export default {
    telegram: telegramUtils,
    cn
};