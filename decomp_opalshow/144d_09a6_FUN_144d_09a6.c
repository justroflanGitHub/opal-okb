
char * __cdecl16far FUN_144d_09a6(char *param_1)

{
  char cVar1;
  char *pcVar2;
  undefined2 uVar3;
  
  uVar3 = (undefined2)((ulong)param_1 >> 0x10);
  cVar1 = *param_1;
  pcVar2 = (char *)param_1;
  while (cVar1 != '\0') {
    if ((byte)(cVar1 + 0x9fU) < 0x1a) {
      *pcVar2 = cVar1 + -0x20;
    }
    pcVar2 = pcVar2 + 1;
    cVar1 = *pcVar2;
  }
  return (char *)param_1;
}

