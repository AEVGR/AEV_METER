// Copyright Peter Müller mupe
//
// Permission is hereby granted, free of charge, to any person obtaining a
// copy of this software and associated documentation files (the
// "Software"), to deal in the Software without restriction, including
// without limitation the rights to use, copy, modify, merge, publish,
// distribute, sublicense, and/or sell copies of the Software, and to permit
// persons to whom the Software is furnished to do so, subject to the
// following conditions:
//
// The above copyright notice and this permission notice shall be included
// in all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
// OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
// MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN
// NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
// DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
// OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
// USE OR OTHER DEALINGS IN THE SOFTWARE.

// SDK Configuratio main task stack size *10
#include <stdio.h>

#include <math.h>
#include <float.h>
#include <string.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include "esp_timer.h"
#include <esp_log.h>
#include "esp_adc/adc_oneshot.h"

#define NOP() asm volatile ("nop")

/**
 * Länge des Buffers für die Glättung der Messergebisse
 */
#define pufferSize  7
/**
 * Anzahl der Sensoren bzw ADC Wandler
 */
#define numSens  7
/**
 * Definiton der ADC Sensoren 3 4 5 6 7 0 1
 */
uint8_t adcNrArray[numSens] = { ADC_CHANNEL_3, ADC_CHANNEL_4, ADC_CHANNEL_5,
		ADC_CHANNEL_6, ADC_CHANNEL_7, ADC_CHANNEL_0, ADC_CHANNEL_1 };
/**
 * Werte der letzten Messungen für die Glättung
 */
float adcHistArray[numSens][pufferSize];

/**
 * letzte gemessene Werte
 */
float adcArray[numSens];
/**
 * Umrechung der gemessenen Werte in Watt2
 */

double filterArray[numSens];

double fx(double x) {
	//return x*0.0214490;
	//return x;
	if (x < 0) {
		return 2.237637E-14 * x * x * x + 1.111419E-8 * x * x + 0.0207136 * x;

	} else {
		return 1.383418E-14 * x * x * x - 1.1124131E-8 * x * x + 0.0230523 * x;
	}

}
/**
 * variable für die unterbruchsfreie Messung
 */
static portMUX_TYPE my_spinlock = portMUX_INITIALIZER_UNLOCKED;

/**
 * warten eine Anzahl Microsekunden
 */
void delayMicroseconds(uint32_t us) {
	uint32_t m = esp_timer_get_time();
	if (us) {
		uint32_t e = (m + us);
		if (m > e) { //overflow
			while (esp_timer_get_time() > e) {
				NOP();
			}
		}
		while (esp_timer_get_time() < e) {
			NOP();
		}
	}
}

/**
 * Messwert vom Sensor x in Watt
 */
double getl(size_t xi) {
	double ret = 0;
	double min = DBL_MAX;
	double max = DBL_MIN;

	for (size_t x = 0; x < pufferSize; ++x) {
		min = min > adcHistArray[xi][x] ? adcHistArray[xi][x] : min;
		max = max < adcHistArray[xi][x] ? adcHistArray[xi][x] : max;

		ret = ret + adcHistArray[xi][x];
	}
	ret = ret - min - max;
	ret = fx((ret / (pufferSize - 2)));

	ret = fabs(ret) < 5 ? ((1.0 * rand()) / RAND_MAX) * -1 : ret;

	return ret;
}
double imgToPol(double imag, double real) {
	double winkel;
	winkel = 2 * atan(imag / (sqrt(real * real + imag * imag) + real));
	return winkel;
}

/**
 * Umrechnung der Sensorwerte in Amplitudenwerte siehe Wikipedia goertzel
 */
double goertzel(int numSamples, int TARGET_FREQUENCY, int SAMPLING_RATE,
		double *data, double winkel) {
	int k, i;
	double floatnumSamples;
	double omega, sine, cosine, coeff, q0, q1, q2, result, real, imag;

	floatnumSamples = (float) numSamples;
	k = (int) (0.5 + ((floatnumSamples * TARGET_FREQUENCY) / SAMPLING_RATE));
	omega = (2.0 * M_PI * k) / floatnumSamples;
	sine = sin(omega);
	cosine = cos(omega);
	coeff = 2.0 * cosine;
	q0 = 0;
	q1 = 0;
	q2 = 0;

	for (i = 0; i < numSamples; i++) {
		q0 = coeff * q1 - q2 + data[i];
		q2 = q1;
		q1 = q0;
	}
	real = (q1 - q2 * cosine);
	imag = (q2 * sine);

	result = sqrt(real * real + imag * imag);

	double win = imgToPol(imag, real);

	double dif = fabs(winkel - win);
//	printf("%lf %lf %lf",dif, winkel,win);

	if (dif < M_PI / 2.0) {
		result = result * -1.0;
	}

	return result;
}

double goertzelWinkel(int numSamples, int TARGET_FREQUENCY, int SAMPLING_RATE,
		double *data) {
	int k, i;
	double floatnumSamples;
	double omega, sine, cosine, coeff, q0, q1, q2, real, imag;

	floatnumSamples = (float) numSamples;
	k = (int) (0.5 + ((floatnumSamples * TARGET_FREQUENCY) / SAMPLING_RATE));
	omega = (2.0 * M_PI * k) / floatnumSamples;
	sine = sin(omega);
	cosine = cos(omega);
	coeff = 2.0 * cosine;
	q0 = 0;
	q1 = 0;
	q2 = 0;

	for (i = 0; i < numSamples; i++) {
		q0 = coeff * q1 - q2 + data[i];
		q2 = q1;
		q1 = q0;
	}
	real = (q1 - q2 * cosine);
	imag = (q2 * sine);

	return imgToPol(imag, real);

}

void mupePowerServerTask() {
	double messwerteArray[numSens][256];
	int adcMesswert;

	uint64_t timerSerialOutput = esp_timer_get_time();
	size_t positionImBuffer = 0;

	/**
	 * inizialisierung der ADC Wandler
	 */
	adc_oneshot_unit_handle_t adc1_handle;
	adc_oneshot_unit_init_cfg_t init_config1 = { .unit_id = ADC_UNIT_1, };
	ESP_ERROR_CHECK(adc_oneshot_new_unit(&init_config1, &adc1_handle));
	adc_oneshot_chan_cfg_t config = { .bitwidth = ADC_BITWIDTH_12, .atten =
			ADC_ATTEN_DB_11, };
	for (int c = 0; c < numSens; c++) {
		ESP_ERROR_CHECK(
				adc_oneshot_config_channel(adc1_handle, adcNrArray[c],
						&config));
	}

	/**
	 * Definition für die unverzögerte Ausgabe der Werte an Serial
	 */
	setbuf(stdout, NULL);
	setvbuf(stdout, NULL, _IONBF, 0); // Disable stout buffering
	uint32_t lauf = 0;

	while (1) {
		taskENTER_CRITICAL(&my_spinlock);
		lauf = 0;
		int last = 0;
		do {
			adc_oneshot_read(adc1_handle, adcNrArray[numSens], &adcMesswert);
			lauf++;
			if (lauf > 100)
				break;
			if (last == adcMesswert)
				break;
			last = adcMesswert;
			delayMicroseconds(100);
		} while (adcMesswert < 4094 / 2);

		do {
			adc_oneshot_read(adc1_handle, adcNrArray[numSens], &adcMesswert);
			lauf++;
			if (lauf > 200)
				break;
			if (last == adcMesswert)
				break;
			last = adcMesswert;
			delayMicroseconds(100);
		} while (adcMesswert > 4094 / 2);

		uint64_t dauerDerMessung = esp_timer_get_time();
		for (int i = 0; i < 256; i++) {
			for (int c = 0; c < numSens; c++) {
				ESP_ERROR_CHECK(
						adc_oneshot_read(adc1_handle, adcNrArray[c],
								&adcMesswert));
				messwerteArray[c][i] = (double) adcMesswert;
			}
			delayMicroseconds(500);
		}
		dauerDerMessung = esp_timer_get_time() - dauerDerMessung;
		taskEXIT_CRITICAL(&my_spinlock);
		printf("lauf %li %i \r\n", lauf, adcMesswert);

		//	printf("time %"PRId64"\n", dauerDerMessung);
		if (timerSerialOutput + 1000000 < esp_timer_get_time()) {

			printf("AEV_METER %.1lf,%.1lf,%.1lf,%.1lf,%.1lf,%.1lf,%.1lf\r\n",
					getl(0), getl(1), getl(2), getl(3), getl(4), getl(5),
					getl(6));
			timerSerialOutput = timerSerialOutput + 1000000;
		}

		int freq = 256.0 / (((float) dauerDerMessung / 1000000));
		double winkel = goertzelWinkel(256, 50, freq,
				messwerteArray[numSens - 1]);
		for (int c = 0; c < numSens; c++) {
			adcHistArray[c][positionImBuffer] = goertzel(256, 50, freq,
					messwerteArray[c], winkel);
			adcArray[c] = adcHistArray[c][positionImBuffer];
		}
		//	printf("\n");
		vTaskDelay(10);
		positionImBuffer++;
		positionImBuffer =
				(positionImBuffer < pufferSize) ? positionImBuffer : 0;
	}
}

void app_main(void) {
	mupePowerServerTask();
}
