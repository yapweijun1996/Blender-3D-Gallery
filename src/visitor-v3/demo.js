import { createVisitorCustomization } from "../../models/gjh-visitor-v3/customization.js";
import { createVisitorDemo } from "../visitor-demo.js";
import "../visitor-v2/style.css";

const variant = {
  createCustomization: createVisitorCustomization,
  appearance: {
    hair: ["wavy", "short"],
    hairColor: ["black", "brown"],
    outfit: ["hoodie", "tee"],
  },
  accessories: ["backpack", "badge", "watch"],
  animations: [
    ["idle", "clip.idle"], ["walk", "clip.walk"], ["run", "clip.run"],
    ["turn_left", "clip.turnLeft"], ["turn_right", "clip.turnRight"],
    ["sit_down", "clip.sitDown"], ["stand_up", "clip.standUp"],
    ["pick_up", "clip.pickUp"], ["carry", "clip.carry"], ["wave", "clip.wave"],
    ["point", "clip.point"], ["push_cart", "clip.pushCart"],
  ],
  looping: ["idle", "walk", "run", "carry", "push_cart"],
};

export default function createVisitorV3Demo(options) {
  return createVisitorDemo(options, variant);
}
