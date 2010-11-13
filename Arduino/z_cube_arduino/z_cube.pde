/*
 * A simple sketch that uses WiServer to get the hourly weather data from LAX and prints
 * it via the Serial API
 */

#include <WiServer.h>

#define WIRELESS_MODE_INFRA	1
#define WIRELESS_MODE_ADHOC	2

// Wireless configuration parameters ----------------------------------------
unsigned char local_ip[] = {192,168,1,100};	// IP address of WiShield
unsigned char gateway_ip[] = {192,168,1,1};	// router or gateway IP address
unsigned char subnet_mask[] = {255,255,255,0};	// subnet mask for the local network
const prog_char ssid[] PROGMEM = {"SmellyCat"};		// max 32 bytes

unsigned char security_type = 3;	// 0 - open; 1 - WEP; 2 - WPA; 3 - WPA2

// WPA/WPA2 passphrase
const prog_char security_passphrase[] PROGMEM = {"abcde12345"};	// max 64 characters

// WEP 128-bit keys
// sample HEX keys
prog_uchar wep_keys[] PROGMEM = { 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d,	// Key 0
				  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,	// Key 1
				  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,	// Key 2
				  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00	// Key 3
				};

// setup the wireless mode
// infrastructure - connect to AP
// adhoc - connect to another WiFi device
unsigned char wireless_mode = WIRELESS_MODE_INFRA;

unsigned char ssid_len;
unsigned char security_passphrase_len;
// End of wireless configuration parameters ----------------------------------------

void jsbGetCol(char* data, int len) {
  while (len-- > 0) {
    Serial.print(*(data++));
  } 
}
// Function that prints data from the server
void printData(char* data, int len) {
  
  // Print the data returned by the server
  // Note that the data is not null-terminated, may be broken up into smaller packets, and 
  // includes the HTTP header. 
  while (len-- > 0) {
    Serial.print(*(data++));
  } 
}


// IP Address for appspot  
uint8 ip[] = {74,125,53,141};

// A request that gets the latest METAR weather data for LAX
GETrequest getColor(ip, 80, "z-cube.appspot.com", "/getcolor?uid=00:00:00:00:00:01&pwd=a");


void setup() {
    // Initialize WiServer (we'll pass NULL for the page serving function since we don't need to serve web pages) 
  WiServer.init(NULL);
  
  // Enable Serial output and ask WiServer to generate log messages (optional)
  Serial.begin(57600);
  WiServer.enableVerboseMode(false);

  // Have the processData function called when data is returned by the server
  getColor.setReturnFunc(printData);
}


// Time (in millis) when the data should be retrieved 
long updateTime = 0;
int has_been_run = 0;
void loop(){

  if (has_been_run == 0) {
    Serial.println("Running the query for the first time.");
    getColor.submit();
    updateTime = millis();
    updateTime += (long)(1000.0 * 45.0);
    Serial.println(updateTime);
    Serial.println(millis());
    //Serial.println("yyy");
    has_been_run = 1;
  }
  
  // Check if it's time to get an update
  if (millis() >= updateTime) {
    if (has_been_run == 1) {
    // Get another udate one hour from now
    Serial.println("Running the query again.");
    updateTime +=  (long)(1000.0 * 45.0);
    getColor.submit();

    }
  }
  
  // Run WiServer
  WiServer.server_task();
 
  delay(1000);
  //Serial.println(updateTime);
  //Serial.println(millis());
  //Serial.println("xxx");
}
