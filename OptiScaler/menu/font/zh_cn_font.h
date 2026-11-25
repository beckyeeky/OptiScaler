#pragma once

#include <fstream>
#include <vector>

// Display-only support for the zh-CN menu. No Windows font is redistributed.
// Read through std::filesystem::path so non-ASCII TTFFontPath values work on Windows.
inline ImFont* LoadZhCnFontFile(ImFontAtlas* atlas, const std::filesystem::path& path, float size,
                                const ImFontConfig& config)
{
    try
    {
        std::ifstream stream(path, std::ios::binary | std::ios::ate);
        if (!stream)
            return nullptr;
        auto length = stream.tellg();
        if (length <= 0 || length > 64 * 1024 * 1024)
            return nullptr;
        std::vector<char> bytes(static_cast<size_t>(length));
        stream.seekg(0);
        if (!stream.read(bytes.data(), static_cast<std::streamsize>(bytes.size())))
            return nullptr;
        ImFontConfig fileConfig = config;
        // ImGui copies the bytes; the local vector may then be destroyed safely.
        fileConfig.FontDataOwnedByAtlas = false;
        // ImGui 1.92+ loads glyphs on demand. Keep explicit ranges for legacy atlas builds too.
        static const ImWchar ranges[] = { 0x0020, 0x00FF, 0x2000, 0x206F, 0x3000, 0x30FF, 0x3400,
                                          0x4DBF, 0x4E00, 0x9FFF, 0xFF00, 0xFFEF, 0 };
        return atlas->AddFontFromMemoryTTF(bytes.data(), static_cast<int>(bytes.size()), size, &fileConfig, ranges);
    }
    catch (const std::exception&)
    {
        return nullptr;
    }
}

inline ImFont* LoadWindowsZhCnFont(ImFontAtlas* atlas, float size, const ImFontConfig& config)
{
    wchar_t windowsDirectory[MAX_PATH] {};
    auto length = GetWindowsDirectoryW(windowsDirectory, MAX_PATH);
    if (length == 0 || length >= MAX_PATH)
        return nullptr;
    const auto fonts = std::filesystem::path(windowsDirectory) / L"Fonts";
    for (const auto* name : { L"msyh.ttc", L"simhei.ttf", L"simsun.ttc" })
    {
        if (auto* font = LoadZhCnFontFile(atlas, fonts / name, size, config))
            return font;
    }
    return nullptr;
}
