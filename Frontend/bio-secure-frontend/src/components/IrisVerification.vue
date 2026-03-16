<script lang="ts">
import { defineComponent, ref, onMounted, onUnmounted } from "vue";

export default defineComponent({
  name: "IrisScanner",
  setup() {
    const wsUri = "ws://127.0.0.1:5000/Iris";
    let websocket: WebSocket | null = null;

    const leye = ref<string>("");
    const reye = ref<string>("");
    const checkL = ref<boolean>(true);
    const checkR = ref<boolean>(true);

    const initWebSocket = () => {
      try {
        if (websocket && websocket.readyState === 1) {
          websocket.close();
        }

        websocket = new WebSocket(wsUri);

        websocket.onopen = () => {
          console.log("CONNECTED");
          websocket?.send("connect");
        };

        websocket.onclose = () => {
          console.log("DISCONNECTED");
        };

        websocket.onmessage = (evt: MessageEvent) => {
          console.log("Raw message:", evt.data);
          const parts = evt.data.split(",");
          const msg_type = parts[0];

          console.log("Message received:", msg_type);

          if (msg_type === "irises") {
            leye.value = `data:image/bmp;base64,${parts[1]}`;
            reye.value = `data:image/bmp;base64,${parts[2]}`;
          } else if (msg_type === "irise_L") {
            leye.value = `data:image/bmp;base64,${parts[1]}`;
            reye.value = "";
          } else if (msg_type === "irise_R") {
            reye.value = `data:image/bmp;base64,${parts[1]}`;
            leye.value = "";
          } else {
            console.log("Unknown message:", evt.data);
          }
        };

        websocket.onerror = (evt) => {
          console.error("ERROR:", evt);
        };
      } catch (exception) {
        console.error("EXCEPTION:", exception);
      }
    };

    const capture = () => {
      leye.value = "";
      reye.value = "";

      if (websocket) {
        if (checkL.value && checkR.value) {
          websocket.send("BOTH_EYES");
          console.log(">>> Sent: BOTH_EYES");
        } else if (checkL.value && !checkR.value) {
          websocket.send("LEFT_EYE");
          console.log(">>> Sent: LEFT_EYE");
        } else if (checkR.value && !checkL.value) {
          websocket.send("RIGHT_EYE");
          console.log(">>> Sent: RIGHT_EYE");
        }
      }
    };

    const stopCapture = () => {
      websocket?.send("stop");
    };

    const stopWebSocket = () => {
      if (websocket) {
        websocket.send("close");
        websocket.close();
      }
    };

    onMounted(() => {
      initWebSocket();
    });

    onUnmounted(() => {
      stopWebSocket();
    });

    return {
      leye,
      reye,
      checkL,
      checkR,
      capture,
      stopCapture,
      stopWebSocket,
    };
  },
});
</script>

<template>
  <div>
    <h1>Iris Identification :: BMT-20 Scanner</h1>
    <div class="flex justify-center py-5">
        <p>
            <button @click="capture" class=" bg-green-500 rounded-lg p-5">Capture</button>
        </p>

    </div>
    
    <div class="bg-blue-200 p-5 rounded-lg w-[80%] mx-auto">
        <div class="gap-5 row">
            <div class="w-[50%]">
                Right Eye: <input type="checkbox" v-model="checkR" />
                <div v-if="!reye">
                    <img src="../assets/IrisScan.png" alt="" class="w-full rounded-lg" />
                </div>
                <div v-else>
                    <img :src="reye" alt="Right Eye" class="w-full rounded-lg" />
                </div>
            </div>

            <div class="w-[50%]">
                Left Eye: <input type="checkbox" v-model="checkL" />
                <div v-if="!leye">
                    <img src="../assets/IrisScan.png" alt="" class="w-full rounded-lg" />
                </div>
                <div v-else>
                    <img :src="leye" alt="Left Eye" class="w-full rounded-lg" />
                </div>
            </div>
        </div>
    </div>

   
  </div>
</template>

<style scoped>
.row {
  display: flex;
}
.column {
  flex: 33.33%;
  padding: 5px;
}
</style>
