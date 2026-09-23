# MicroARCA Teste 1.0.0

Biblioteca original do Projeto ARCA, sob licença MIT, para testar descoberta,
download, verificação e instalação pela IDE. Sem dependências, imports,
acesso ao hardware ou efeitos colaterais ao importar.

Instale `lib_microarca_teste.py` em `/lib` no ESP32 e execute:

```python
import lib_microarca_teste as teste

print(teste.ola("ARCA"))       # Ola, ARCA!
print(teste.somar(2, 3))        # 5
print(teste.dobrar(7))          # 14
print(teste.eh_par(4))          # True
print(teste.contar_ate(5))      # [1, 2, 3, 4, 5]
```

`somar` e `dobrar` recebem números. `eh_par` e `contar_ate` recebem inteiros;
use limites pequenos em `contar_ate`, pois a lista ocupa memória no ESP32.
`ola()` usa "MicroARCA" quando nenhum nome é passado.
