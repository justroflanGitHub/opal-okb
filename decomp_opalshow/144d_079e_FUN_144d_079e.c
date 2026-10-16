
int __cdecl16far FUN_144d_079e(char *param_1)

{
  char *pcVar1;
  uint uVar2;
  char *pcVar3;
  
  pcVar3 = (char *)param_1;
  uVar2 = 0xffff;
  do {
    if (uVar2 == 0) break;
    uVar2 = uVar2 - 1;
    pcVar1 = pcVar3;
    pcVar3 = pcVar3 + 1;
  } while (*pcVar1 != '\0');
  return ~uVar2 - 1;
}

