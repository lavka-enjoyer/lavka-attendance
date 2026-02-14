import React, { useState } from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import PixelIcon from '@/components/PixelIcon';
import { PixelCheckbox } from '@/components/PixelCheckbox';

const MarkSelfScreen = ({ userData, onMarkSelf, onMarkMultiple, onBack }) => {
  const [allowOthersToMark, setAllowOthersToMark] = useState(false);
  
  const handleMarkSelf = () => {
    // This would typically call an API
    onMarkSelf();
  };
  
  const handleAllowOthersToggle = () => {
    setAllowOthersToMark(!allowOthersToMark);
  };
  
  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader className="text-center">
        <h2 className="text-xl font-pixel mb-2">{userData?.FIO || 'Фамилия Имя Отчество'}</h2>
        <p className="text-sm font-pixel">{userData?.group || 'Группа'}</p>
      </CardHeader>
      <CardContent className="space-y-4">
        <Button
          className="w-full h-12 font-pixel border-2 border-black flex items-center justify-center"
          onClick={handleMarkSelf}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="mr-2">
            <rect x="10" y="6" width="4" height="4" fill="currentColor" />
            <rect x="8" y="10" width="8" height="2" fill="currentColor" />
            <rect x="6" y="12" width="12" height="2" fill="currentColor" />
            <rect x="6" y="14" width="12" height="4" fill="currentColor" />
          </svg>
          Отметить себя
        </Button>

        <Button
          className="w-full h-12 font-pixel border-2 border-black flex items-center justify-center"
          onClick={onMarkMultiple}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="mr-2">
            <rect x="8" y="6" width="4" height="4" fill="currentColor" />
            <rect x="16" y="6" width="4" height="4" fill="currentColor" />
            <rect x="6" y="10" width="6" height="2" fill="currentColor" />
            <rect x="14" y="10" width="6" height="2" fill="currentColor" />
            <rect x="10" y="14" width="4" height="4" fill="currentColor" />
            <rect x="8" y="18" width="8" height="2" fill="currentColor" />
          </svg>
          Отметить несколько
        </Button>

        <div className="mt-4 pt-4 border-t-2 border-dashed border-black">
          <div className="flex items-center justify-between">
            <div onClick={handleAllowOthersToggle} className="flex items-center cursor-pointer">
              <PixelCheckbox 
                checked={allowOthersToMark} 
                onChange={handleAllowOthersToggle}
              />
              <span className="ml-2 font-pixel text-sm">Разрешать меня отмечать</span>
            </div>
          </div>
          <p className="text-xs font-pixel mt-2 text-gray-500">
            Выключайте, если вы отсутствуете официально
          </p>
        </div>
      </CardContent>
    </Card>
  );
};

export default MarkSelfScreen;