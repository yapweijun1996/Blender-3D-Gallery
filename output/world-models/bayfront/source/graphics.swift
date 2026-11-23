import AppKit

let args = CommandLine.arguments
let mode = args[1]
let fm = FileManager.default
func color(_ hex: UInt32) -> NSColor {
    NSColor(srgbRed: CGFloat((hex >> 16) & 255)/255, green: CGFloat((hex >> 8) & 255)/255, blue: CGFloat(hex & 255)/255, alpha: 1)
}
func rect(_ x: CGFloat, _ y: CGFloat, _ w: CGFloat, _ h: CGFloat, _ hex: UInt32) {
    color(hex).setFill()
    NSBezierPath(rect: NSRect(x:x,y:y,width:w,height:h)).fill()
}
func word(_ string: String, _ x: CGFloat, _ y: CGFloat, _ size: CGFloat, _ hex: UInt32 = 0xffffff, _ bold: Bool = true) {
    (string as NSString).draw(at: NSPoint(x:x,y:y), withAttributes: [
        .font: NSFont.systemFont(ofSize:size,weight:bold ? .bold : .medium),
        .foregroundColor:color(hex)
    ])
}
func canvas(_ w: Int, _ h: Int, _ url: String, _ quality: Double, _ draw: () -> Void) {
    let bitmap = NSBitmapImageRep(bitmapDataPlanes:nil,pixelsWide:w,pixelsHigh:h,bitsPerSample:8,samplesPerPixel:4,hasAlpha:true,isPlanar:false,colorSpaceName:.deviceRGB,bytesPerRow:0,bitsPerPixel:0)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep:bitmap)
    NSGraphicsContext.current?.imageInterpolation = .high
    draw()
    NSGraphicsContext.current?.flushGraphics()
    NSGraphicsContext.restoreGraphicsState()
    try! bitmap.representation(using:.jpeg,properties:[.compressionFactor:quality])!.write(to:URL(fileURLWithPath:url))
}
let orange: UInt32 = 0xf5a300
let blue: UInt32 = 0x096fc0
let teal: UInt32 = 0x006a67
let black: UInt32 = 0x17222a
if mode == "atlas" {
    let mapCircle = args[3] != "downtown"
    let line = mapCircle ? orange : blue
    canvas(1024,1024,args[2],0.94) {
        for i in 0..<8 {
            let y = CGFloat(i * 128)
            rect(0,y,1024,128,[teal,black,black,0xf6f5eb,teal,black,0xf6f5eb,teal][i])
            switch i {
            case 0:
                word("Bayfront",30,y+24,76)
                rect(375,y+23,130,79,orange)
                word("CE1",389,y+36,47,black)
                rect(517,y+23,144,79,blue)
                word("DT16",525,y+36,47)
                word("MRT  EXIT",697,y+41,40)
                rect(915,y+20,86,88,0xf4d66d)
                word("B",934,y+25,63,black)
            case 1:
                word("↑  Circle Line",28,y+61,42)
                word("↑  Downtown Line",28,y+9,37)
                rect(407,y+68,124,40,orange)
                rect(407,y+18,124,40,blue)
                word("CE1",431,y+70,28,black)
                word("DT16",423,y+20,28)
                word("Way out  →",671,y+60,43,0xf6dc70)
                word("Marina Bay Sands",671,y+16,29)
            case 2:
                word("↑  Way out",27,y+51,60,0xf5d76d)
                word("B   C   D",410,y+43,58,0xf5d76d)
                word("Lift  →",768,y+46,52)
            case 3:
                rect(0,y+18,1024,10,line)
                let stops = mapCircle ? ["Dhoby Ghaut","Promenade","Bayfront","Marina Bay"] : ["Bugis","Promenade","Bayfront","Downtown","Telok Ayer","Chinatown"]
                word(mapCircle ? "Circle Line   •   Bayfront" : "Downtown Line   •   Bayfront",26,y+82,34,black)
                for (index, stop) in stops.enumerated() {
                    let x = 30 + CGFloat(index) * (mapCircle ? 236 : 165)
                    color(index == 2 ? black : line).setFill()
                    NSBezierPath(ovalIn:NSRect(x:x,y:y+14,width:18,height:18)).fill()
                    word(stop,x,y+37,mapCircle ? 26 : 20,black)
                }
            case 4:
                word("Bayfront",25,y+22,74)
                word("海湾舫",405,y+33,51)
                rect(748,y+23,246,80,line)
                word(mapCircle ? "CE1" : "DT16",787,y+27,61,mapCircle ? black : 0xffffff)
            case 5:
                word("Passenger Service Centre",25,y+28,57)
            case 6:
                rect(24,y+22,82,82,0xf3cf56)
                word("!",54,y+23,64,black)
                word("Please stand behind the yellow line",132,y+38,46,black)
            default:
                word("↓   Marina Bay Sands",25,y+24,66)
                rect(911,y+21,83,86,0xf4d66d)
                word("B",930,y+24,62,black)
            }
        }
    }
} else {
    let model = args[3]
    let labels = args.dropFirst(4)
    canvas(1800,1140,args[2],0.92) {
        rect(0,0,1800,1140,0x101b24)
        word(model,26,1060,37)
        word("BAYFRONT MRT  /  SINGAPORE",26,1029,18,0x92b5bf)
        for (i,label) in labels.enumerated() {
            let x = CGFloat(24 + (i % 3) * 588)
            let y = CGFloat(25 + (1-i/3) * 500)
            let frame = NSRect(x:x,y:y+44,width:576,height:450)
            rect(x,y+44,576,450,0x202c37)
            let filename = ".qa/\(model)_\(i).png"
            NSImage(contentsOfFile:filename)!.draw(in:frame,from:.zero,operation:.sourceOver,fraction:1)
            word(label,x,y+8,20,0xbdd4da)
        }
    }
}
