import fs from 'fs';
import JavaScriptObfuscator from 'javascript-obfuscator';

console.log("🔒 Đang mã hóa server.js...");

try {
    const source = fs.readFileSync('server.js', 'utf8');

    const result = JavaScriptObfuscator.obfuscate(source, {
        compact: true,
        controlFlowFlattening: true,
        controlFlowFlatteningThreshold: 0.75,
        deadCodeInjection: true,
        deadCodeInjectionThreshold: 0.4,
        debugProtection: true,
        debugProtectionInterval: 4000,
        disableConsoleOutput: true,
        identifierNamesGenerator: 'hexadecimal',
        log: false,
        numbersToExpressions: true,
        renameGlobals: false,
        selfDefending: true,
        simplify: true,
        splitStrings: true,
        splitStringsChunkLength: 10,
        stringArray: true,
        stringArrayCallsTransform: true,
        stringArrayEncoding: ['rc4'],
        stringArrayIndexShift: true,
        stringArrayRotate: true,
        stringArrayShuffle: true,
        stringArrayWrappersCount: 2,
        stringArrayWrappersChainedCalls: true,
        stringArrayWrappersParametersMaxCount: 4,
        stringArrayWrappersType: 'function',
        stringArrayThreshold: 0.75,
        target: 'node'
    });

    fs.writeFileSync('server.prod.js', result.getObfuscatedCode());

    console.log("✅ Đã mã hóa xong: server.prod.js");
    console.log("👉 Chạy server mã hóa bằng lệnh: node server.prod.js");
} catch (e) {
    console.error("❌ Lỗi obfuscation:", e);
    process.exit(1);
}
