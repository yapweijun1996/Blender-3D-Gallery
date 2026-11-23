import { createVisitorCustomization } from "../../models/gjh-mall-visitor-v2/customization.js";
import { createVisitorDemo } from "../visitor-demo.js";
import "./style.css";

const variant = {
  createCustomization: createVisitorCustomization,
  appearance: {
    hair: ["swept", "short"],
    hairColor: ["brown", "black"],
    outfit: ["polo", "hoodie"],
  },
  accessories: ["glasses", "backpack", "watch"],
  animations: [
    ["idle", "clip.idle"], ["walk", "clip.walk"], ["sprint", "clip.run"],
    ["sit", "clip.sit"], ["stand", "clip.stand"], ["pickup", "clip.pickUp"],
    ["place", "clip.putDown"], ["push", "clip.push"], ["elevator", "clip.reach"],
  ],
  looping: ["idle", "walk", "sprint", "push"],
};

export default function createVisitorV2Demo(options) {
  return createVisitorDemo(options, variant);
}
