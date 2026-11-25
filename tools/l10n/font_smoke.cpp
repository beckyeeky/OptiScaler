#define NOMINMAX
#include <Windows.h>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <imgui/imgui.h>
#include <imgui/imgui_internal.h>
#include "../../OptiScaler/menu/font/zh_cn_font.h"

int main()
{
    ImGui::CreateContext();
    auto* atlas = ImGui::GetIO().Fonts;
    ImFontConfig config;
    if (LoadZhCnFontFile(atlas, L"missing-font.ttf", 14.0f, config) != nullptr)
        return 1;
    std::ofstream("invalid-font.ttf", std::ios::binary) << "not a font";
    if (LoadZhCnFontFile(atlas, L"invalid-font.ttf", 14.0f, config) != nullptr)
        return 2;
    auto* font = LoadWindowsZhCnFont(atlas, 14.0f, config);
    if (!font)
        return 3;
    auto* baked = font->GetFontBaked(14.0f);
    std::ifstream chars("required-chars.txt");
    unsigned int code, count = 0;
    while (chars >> code)
    {
        if (!baked->FindGlyphNoFallback(static_cast<ImWchar>(code)))
        {
            std::cerr << "Missing glyph: " << code << '\n';
            return 4;
        }
        ++count;
    }
    if (!count)
        return 5;
    wchar_t windowsDirectory[MAX_PATH] {};
    GetWindowsDirectoryW(windowsDirectory, MAX_PATH);
    const auto source = std::filesystem::path(windowsDirectory) / L"Fonts" / L"msyh.ttc";
    const auto unicodePath = std::filesystem::path(L"中文字体测试.ttc");
    std::filesystem::copy_file(source, unicodePath, std::filesystem::copy_options::overwrite_existing);
    if (!LoadZhCnFontFile(atlas, unicodePath, 14.0f, config))
        return 6;
    // Exercise the same custom-font + system-font merge used by the menu.
    ImFontConfig mergeConfig;
    mergeConfig.MergeMode = true;
    if (!LoadWindowsZhCnFont(atlas, 14.0f, mergeConfig))
        return 7;
    ImGui::DestroyContext();
    std::filesystem::remove(unicodePath);
    std::filesystem::remove("invalid-font.ttf");
    std::cout << "PASS: " << count << " translated non-ASCII glyphs; Unicode path; missing/invalid font; system merge\n";
}
