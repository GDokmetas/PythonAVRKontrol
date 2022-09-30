
#include <avr/io.h>
void setup() {
Serial.begin(500000);
TCCR1A = 0;
TCCR1B = 0;
TCCR1C = 0;
TCNT1 = 0;
ICR1 = 0;
OCR1A = 0;
OCR1B = 0;
TCCR2A = 0;
TCCR2B = 0;
TCNT2 = 0;
OCR2A = 0;
OCR2B = 0;
}

void loop() {
while(Serial.available() == 0) {}
delay(1);
unsigned char rw = Serial.read();
unsigned char *ptr = Serial.read();
unsigned char val = Serial.read();
if(rw == 0)
{
  Serial.write(*ptr);
}

if(rw == 1)
{
  *ptr = val;
}

}
