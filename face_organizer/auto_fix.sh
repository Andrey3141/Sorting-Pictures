#!/bin/bash
while true; do
    echo "🔨 Сборка..."
    output=$(flutter build apk --debug 2>&1)
    echo "$output"
    
    # Ищем путь к недостающему файлу
    path=$(echo "$output" | grep -oP "(?<=> ).*?/META-INF/com/android/build/gradle/aar-metadata.properties" | head -1)
    if [ -z "$path" ]; then
        # Если ошибка не о файле, выходим
        echo "$output" | grep -q "BUILD SUCCESSFUL" && echo "✅ Сборка успешна!" && break
        echo "❌ Неизвестная ошибка, выходим"
        break
    fi
    
    echo "📁 Создаём недостающий файл: $path"
    mkdir -p "$(dirname "$path")"
    touch "$path"
    echo "✅ Файл создан, повторяем сборку..."
done
