#include <ArduinoJson.h>
#include <ESP8266WiFi.h>
#include <EEPROM.h>
#include <FS.h>


/*      CONFIG    */

#define port 42000
#define ap "greenbox"
#define secret "newpassword"


IPAddress ip(192, 168, 4, 20);
IPAddress dns(8, 8, 8, 8);
IPAddress gateway(192, 168, 4, 200);
IPAddress subnet(255, 255, 255, 0);


/*      INIT      */

WiFiServer server(port);
StaticJsonBuffer<200> jsonBuffer;
JsonObject& jdata = jsonBuffer.createObject();


void handle_request(WiFiClient client) {
  boolean blank_line = true;
  while (client.connected()) {
    if (client.available()) {
      char c = client.read();
      if (c == '\n' && blank_line) {
        selectMuxPin(0);

        // all this stuff will be changed 
        jdata["celsius"] = get_temp();
        jdata["humidity"] = get_humidity();
        jdata["heat index"] = dht.computeHeatIndex(jdata["celsius"], jdata["humidity"], false);
        jdata["ph"] = get_ph();
        jdata["ec"] = get_ec();
        jdata["reservoir"] = get_restemp();
        jdata["ph raw mV"] = get_ph_raw();
        //        jdata["potentiometer"] = get_potentiometer();


        client.println("HTTP/1.1 200 OK");
        client.println("Content-Type: text/html");
        client.println("Connection: close\n");
        jdata.printTo(client);
        client.println();
        break;
      }
      if (c == '\n') {
        // when starts reading a new line
        blank_line = true;
      }
      else if (c != '\r') {
        // when finds a character on the current line
        blank_line = false;
      }
    }
  }
  client.stop();
  blink(50);
  blink(50);
  blink(50);
  blink(50);
}



/*      MAIN PROGRAM      */

void setup() {
  Serial.begin(115200);
  pinMode(BUILTIN_LED, OUTPUT); // blinker
  pinMode(zIn, INPUT);
  pinMode(selectPins[0], OUTPUT);
  pinMode(selectPins[1], OUTPUT);
  pinMode(selectPins[2], OUTPUT);

  WiFi.mode(WIFI_AP);
  Serial.print("\nSetting soft-AP configuration ... ");
  Serial.println(WiFi.softAPConfig(ip, gateway, subnet) ? "Ready" : "Failed!");
  Serial.print("Setting soft-AP ... ");
  Serial.println(WiFi.softAP(ap, secret) ? "Ready" : "Failed!");
  Serial.print("Soft-AP IP address = ");
  Serial.println(WiFi.softAPIP());
  server.begin();
  blink(50);
  WiFi.begin();
  blink(50);
  dht.begin();
  blink(50);
  TempProcess(StartConvert);   //let the DS18B20 start the convert
  blink(50);

}

void loop() {
  WiFiClient client = server.available();
  if (client) {
    handle_request(client);
  }

  delay(300);
}

/*      HELPER FUNCTIONS    */

void blink(int delaytime) {
  digitalWrite(BUILTIN_LED, LOW);  // actually is high
  delay(delaytime);
  digitalWrite(BUILTIN_LED, HIGH);  // actually is low
  delay(delaytime);
}
