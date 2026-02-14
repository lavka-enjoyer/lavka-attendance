import React, { useState } from 'react';
import { Card, CardHeader, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import PixelIcon from '@/components/PixelIcon';
import { PixelCheckbox } from '@/components/PixelCheckbox';

const AttendanceSelector = ({ onBack, onSubmit, studentList = [] }) => {
  const [selectedStudents, setSelectedStudents] = useState([]);

  const handleStudentToggle = (studentId) => {
    setSelectedStudents(prev => {
      if (prev.includes(studentId)) {
        return prev.filter(id => id !== studentId);
      } else {
        return [...prev, studentId];
      }
    });
  };

  const handleSubmit = () => {
    // Here we would normally make an API call, but we're using a stub
    onSubmit(selectedStudents);
  };

  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader className="text-center border-b-4 border-black">
        <h2 className="text-2xl font-pixel mb-2">Выбери кого отметить</h2>
      </CardHeader>
      <CardContent className="p-4">
        <div className="space-y-2">
          {studentList.map(student => (
            <div key={student.id} className="flex items-center justify-between p-2 border-b-2 border-dashed border-black">
              <span className="font-pixel">{student.name}</span>
              <PixelCheckbox 
                checked={selectedStudents.includes(student.id)}
                onChange={() => handleStudentToggle(student.id)}
              />
            </div>
          ))}
        </div>
      </CardContent>
      <CardFooter className="flex justify-between border-t-4 border-black">
        <Button 
          variant="outline" 
          onClick={onBack}
          className="flex items-center font-pixel"
        >
          <PixelIcon icon="ArrowLeft" className="mr-2" />
          Вернуться назад
        </Button>
        <Button
          onClick={handleSubmit}
          className="flex items-center font-pixel"
          disabled={selectedStudents.length === 0}
        >
          Начать отметку
          <PixelIcon icon="QrCode" className="ml-2" />
        </Button>
      </CardFooter>
    </Card>
  );
};

export default AttendanceSelector;